# FILE: backend/agents/future_works_agent.py

import logging
from typing import List, Dict, Any, Tuple
from models.schemas import Paper
import asyncio
import torch

logger = logging.getLogger(__name__)

class FutureWorksAgent:
    def __init__(self, model, tokenizer):
        """
        Initialize the FutureWorksAgent with a transformers LLM model and tokenizer.
        
        Args:
            model: The pre-trained language model instance.
            tokenizer: The tokenizer associated with the model.
        """
        self.model = model.to("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = tokenizer

    async def create_improvement_plan(self, papers: List[Paper]) -> Dict[str, Any]:
        """
        Generate an improvement plan based on the selected papers.
        
        Args:
            papers (List[Paper]): A list of Paper objects containing details of each paper.
        
        Returns:
            Dict[str, Any]: A dictionary containing the improvement plan, findings, and metrics.
        """
        try:
            # Construct the prompt
            prompt = self.create_prompt(papers)

            # Generate the improvement plan using the LLM
            improvement_plan = await self.llm_generate_async(prompt)

            # Analyze the improvement plan to extract findings and metrics
            findings, metrics = self.analyze_improvement_plan(improvement_plan)

            return {
                "improvement_plan": improvement_plan,
                "findings": findings,
                "metrics": metrics
            }

        except Exception as e:
            logger.error(f"Review generation error: {e}")
            raise

    def create_prompt(self, papers: List[Paper]) -> str:
        """
        Create a well-structured prompt for the LLM.
        
        Args:
            papers (List[Paper]): A list of Paper objects.
        
        Returns:
            str: The formatted prompt string.
        """
        papers_text = "\n\n".join([
            f"Title: {p.title}\nYear: {p.year}\nAbstract: {p.abstract}"
            for p in papers
        ])
        prompt = (
            "Using the key findings from the following papers:\n\n"
            f"{papers_text}\n\n"
            "Generate an improvement plan that includes novel contributions and suggestions for new research directions. "
            "Structure it as a cohesive plan.\n\n"
            "Summary of the work presented:\n"
        )
        return prompt

    async def llm_generate_async(self, prompt: str) -> str:
        """
        Asynchronously generate text using the transformers LLM.
        
        Args:
            prompt (str): The input prompt for the LLM.
        
        Returns:
            str: The generated improvement plan.
        """
        loop = asyncio.get_event_loop()
        try:
            # Run the synchronous generate method in a thread pool to prevent blocking
            improvement_plan = await loop.run_in_executor(None, self.llm_generate, prompt)
            return improvement_plan
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "Failed to generate improvement plan."

    def llm_generate(self, prompt: str) -> str:
        """
        Synchronously generate text using the transformers LLM.
        
        Args:
            prompt (str): The input prompt for the LLM.
        
        Returns:
            str: The generated improvement plan.
        """
        try:
            # Encode the prompt
            input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.model.device)

            # Generate output tokens
            output_ids = self.model.generate(
                input_ids,
                max_length=1024,  # Reduced max_length for faster generation
                num_return_sequences=1,
                no_repeat_ngram_size=3,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                eos_token_id=self.tokenizer.eos_token_id
            )

            # Decode the generated tokens
            improvement_plan = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

            # Post-process to remove the prompt from the output if it gets included
            summary_start = improvement_plan.find("Summary of the work presented:")
            if summary_start != -1:
                improvement_plan = improvement_plan[summary_start + len("Summary of the work presented:"):].strip()

            return improvement_plan
        except Exception as e:
            logger.error(f"Synchronous LLM generation error: {e}")
            return "Failed to generate improvement plan."

    def analyze_improvement_plan(self, plan: str) -> Tuple[List[str], Dict[str, Any]]:
        """
        Analyze the improvement plan to extract findings and metrics.
        
        Args:
            plan (str): The generated improvement plan.
        
        Returns:
            Tuple[List[str], Dict[str, Any]]: A tuple containing a list of findings and a dictionary of metrics.
        """
        # TODO: Implement actual analysis logic based on the generated plan
        # Placeholder implementation
        findings = [
            "Finding 1: Enhanced methodology improves accuracy by 15%.",
            "Finding 2: Incorporating X technique reduces computational overhead."
        ]
        metrics = {
            "accuracy_improvement": 0.15,
            "computational_efficiency_gain": 0.20
        }

        return findings, metrics