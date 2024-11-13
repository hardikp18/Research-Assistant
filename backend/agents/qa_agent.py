from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict, Optional, Union, Any
import torch
import logging
import asyncio
from models.schemas import Paper
from services.text_processing import TextProcessingService
from services.image_processing import ImageProcessingService

logger = logging.getLogger(__name__)

class QAAgent:
    def __init__(self):
        self.qa_pipeline = pipeline("question-answering")
        self.text_processor = TextProcessingService()
        self.image_processor = ImageProcessingService()
        self.llm = AutoModelForCausalLM.from_pretrained("gpt2")
        self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.llm.to(self.device)

    async def _generate_answer(self, question: str, context: str) -> Dict:
        try:
            # Get initial answer from QA pipeline (optional)
            qa_result = await asyncio.to_thread(
                self.qa_pipeline,
                question=question,
                context=context[:500]  # Truncate context if needed
            )

            # Simplify the prompt
            prompt = f"Question: {question}\nAnswer:"

            inputs = self.tokenizer.encode(prompt, return_tensors='pt').to(self.device)

            max_new_tokens = 150  # Limit the length of the generated answer

            outputs = self.llm.generate(
                inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                no_repeat_ngram_size=3,
                eos_token_id=self.tokenizer.eos_token_id
            )

            # Decode and extract the answer
            generated_text = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )
            # Remove the prompt from the generated text
            answer = generated_text[len(prompt):].strip()

            return {
                "text": answer,
                "confidence": qa_result.get("score", 0.0)
            }

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                "text": "Failed to generate answer",
                "confidence": 0.0
            }
    

    async def _process_paper(self, paper: Paper, question: str) -> Optional[Dict]:
        """Enhanced single paper processing with image support"""
        if not paper.abstract and not paper.full_text:
            return None
            
        content = paper.full_text if paper.full_text else paper.abstract
        relevant_text = self.text_processor.extract_relevant_text(content, question)
        
        # Handle image questions
        if paper.images and self._is_image_question(question):
            image_texts = await self._process_image_question(paper, question)
            if image_texts:
                relevant_text += "\n" + image_texts
            
        return {
            "paper_id": paper.id,
            "title": paper.title,
            "text": relevant_text,
            "year": paper.year,
            "context": self._find_exact_context(content, relevant_text)
        }

    def _find_exact_context(self, full_text: str, relevant_text: str) -> List[Dict]:
        """Find exact locations of relevant text in paper"""
        contexts = []
        paragraphs = full_text.split('\n\n')
        
        for i, para in enumerate(paragraphs):
            if relevant_text in para:
                contexts.append({
                    "section": f"Paragraph {i+1}",
                    "text": para,
                    "excerpt": relevant_text
                })
        return contexts

    async def _process_image_question(self, paper: Paper, question: str) -> str:
        """Enhanced image processing with chart/graph detection"""
        image_texts = []
        for img in paper.images or []:
            # Process image based on type
            if "chart" in img.get("type", "").lower():
                img_text = await self.image_processor.analyze_chart(img["data"])
            elif "graph" in img.get("type", "").lower():
                img_text = await self.image_processor.analyze_graph(img["data"])
            else:
                img_text = await self.image_processor.analyze_image(img["data"])
                
            image_texts.append(f"Figure {img['index']} ({img.get('type', 'image')}) "
                             f"on page {img['page']}: {img_text}")
        return "\n".join(image_texts)

    def _format_response(self, answer: Dict, contexts: List[Dict], combined_context: str) -> Dict:
        """Enhanced response formatting with exact citations"""
        return {
            "text": answer["text"],
            "confidence": answer.get("confidence", 0.0),
            "sources": [
                {
                    "paper_id": ctx["paper_id"],
                    "title": ctx["title"],
                    "year": ctx["year"],
                    "excerpt": ctx["text"],
                    "context": ctx.get("context", [])
                }
                for ctx in contexts
            ],
            "context_used": combined_context
        }

    async def answer_question(self, papers: List[Paper], question: str) -> Dict:
        """Handle both single and multi-paper questions"""
        if not papers or not question:
            raise ValueError("Papers list and question cannot be empty")
            
        try:
            # Process single paper in detail
            if len(papers) == 1:
                context = await self._process_paper(papers[0], question)
                if not context:
                    raise ValueError("No relevant content found in paper")
                    
                answer = await self._generate_answer(question, context["text"])
                return self._format_response(answer, [context], context["text"])
            
            # Process multiple papers
            all_contexts = await self._gather_contexts(papers, question)
            sorted_contexts = self.text_processor.rank_contexts(all_contexts, question)
            combined_context = self._combine_contexts(sorted_contexts[:3])
            
            answer = await self._generate_answer(question, combined_context)
            return self._format_response(answer, sorted_contexts[:3], combined_context)
            
        except Exception as e:
            logger.error(f"Error in answer_question: {e}")
            raise

    async def _gather_contexts(self, papers: List[Paper], question: str) -> List[Dict]:
        """Gather relevant contexts from papers"""
        contexts = []
        for paper in papers:
            try:
                context = await self._process_paper(paper, question)
                if context:
                    contexts.append(context)
            except Exception as e:
                logger.warning(f"Error processing paper {paper.id}: {e}")
                continue
        return contexts

    async def _process_paper(self, paper: Paper, question: str) -> Optional[Dict]:
        """Process individual paper for relevant context"""
        content = paper.abstract
        if not content:
            return None
            
        # relevant_text = self.text_processor.extract_relevant_text(content, question)
        
        # if paper.images and self._is_image_question(question):
        #     image_text = await self._process_image_question(paper, question)
        #     relevant_text += "\n" + image_text
            
        return {
            "paper_id": paper.id,
            "title": paper.title,
            "text": content,
            "year": paper.year
        }

    @staticmethod
    def _is_image_question(question: str) -> bool:
        """Check if question is related to images"""
        image_keywords = {"image", "figure", "chart", "graph", "diagram", "plot"}
        return any(word in question.lower() for word in image_keywords)

    def _combine_contexts(self, contexts: List[Dict]) -> str:
        """Combine contexts with proper citations"""
        return "\n\n".join([
            f"From {ctx['title']} ({ctx['year']}):\n{ctx['text']}"
            for ctx in contexts
        ])

    def _format_response(self, answer: Dict, contexts: List[Dict], combined_context: str) -> Dict:
        """Format the final response"""
        return {
            "text": answer["text"],
            "confidence": answer.get("confidence", 0.0),
            "sources": [
                {
                    "paper_id": ctx["paper_id"],
                    "title": ctx["title"],
                    "year": ctx["year"],
                    "excerpt": ctx["text"][:200] + "..."
                }
                for ctx in contexts
            ],
            "context_used": combined_context[:1000]
        }

    @torch.no_grad()
    def _generate_llm_response(self, prompt: str) -> Dict:
        """Generate LLM response with proper resource handling"""
        try:
            inputs = self.llm_tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024
            ).to(self.device)
            
            outputs = self.llm.generate(
                **inputs,
                max_length=2048,  # Increased output length
                num_return_sequences=1,
                no_repeat_ngram_size=3,
                temperature=0.7,
                top_p=0.9,
                do_sample=True
            )
            
            response = self.llm_tokenizer.decode(
                outputs[0],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )
            
            return {"text": response}
            
        except Exception as e:
            logger.error(f"Error in LLM response generation: {e}")
            return {"text": "Failed to generate response"}