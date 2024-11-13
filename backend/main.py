from fastapi import FastAPI, HTTPException
from models.schemas import (
    PaperRequest,
    QuestionRequest,
    ReviewRequest,
    SearchRequest,
    FutureWorkRequest,
    ImprovementPlanRequest,
    GenerateReviewRequest
)

from transformers import AutoModelForCausalLM, AutoTokenizer
from agents.search_agent import SearchAgent
from agents.qa_agent import QAAgent
from agents.future_works_agent import FutureWorksAgent
from database.neo4j_handler import Neo4jHandler
from services.pdf_processing import PDFProcessingService
import logging
from pydantic import BaseModel
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Initialize database handler
try:
    db_handler = Neo4jHandler(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="Hardik18"
    )
    logger.info("Connected to Neo4j database successfully.")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise

# Initialize LLM
try:
    tokenizer = AutoTokenizer.from_pretrained("facebook/opt-1.3b")
    model = AutoModelForCausalLM.from_pretrained("facebook/opt-1.3b")
    logger.info("LLM loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load LLM: {e}")
    raise

# Initialize agents
search_agent = SearchAgent(db_handler)
qa_agent = QAAgent()
future_works_agent = FutureWorksAgent(model=model, tokenizer=tokenizer)
pdf_service = PDFProcessingService()


@app.post("/search")
async def search_papers(request: SearchRequest):
    """
    Endpoint to search for papers based on a topic.
    """
    try:
        papers = await search_agent.search_papers(request.topic)
        if not papers:
            return {"status": "success", "papers": [], "message": "No papers found"}
        
        # Process PDFs for each paper
        processed_papers = []
        for paper in papers:
            try:
                # Get PDF content
                pdf_content = await pdf_service.process_pdf_url(paper.url)
                if pdf_content:
                    paper.full_text = pdf_content.get("text", "")
                    paper.images = pdf_content.get("images", [])
                
                processed_papers.append({
                    "id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "year": paper.year,
                    "url": paper.url,
                    "has_full_text": bool(paper.full_text),
                    "has_images": bool(paper.images)
                })
                
                # Store processed paper in the database
                await search_agent._store_paper_safe(paper)
                
            except Exception as e:
                logger.warning(f"Error processing PDF for paper {paper.id}: {e}")
                processed_papers.append({
                    "id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "year": paper.year,
                    "url": paper.url,
                    "has_full_text": False,
                    "has_images": False
                })
                
        return {
            "status": "success",
            "papers": processed_papers,
            "count": len(processed_papers)
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error searching papers: {str(e)}"
        )


@app.post("/answer")
async def answer_question(request: QuestionRequest):
    """
    Endpoint to answer questions based on selected papers.
    """
    try:
        # Validate request data
        if not request.paper or not request.question:
            raise HTTPException(
                status_code=422,
                detail="Both paper_ids and question are required"
            )

        # Extract papers from the request
        papers = request.paper  # Assuming 'paper' is a list of paper dictionaries

        # Check if papers are provided
        if not papers:
            raise HTTPException(
                status_code=404, 
                detail="No papers provided for answering the question"
            )
        
        # Get answer using both paper content and images
        answer = await qa_agent.answer_question(papers, request.question)
        
        return {
            "answer": answer.get("text", ""),
            "confidence": answer.get("confidence", 0.0),
            "sources": answer.get("sources", []),
            "context_used": answer.get("context_used", "")
        }
       
    except HTTPException as he:
        # Re-raise HTTPExceptions to let FastAPI handle them appropriately
        logger.error(f"Answer error: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Answer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/future_work")
async def future_work(request: FutureWorkRequest):
    """
    Endpoint to generate future work ideas based on selected papers.
    """
    try:
        # Retrieve full paper details from the database
        papers = []
        for paper_id in request.paper_ids:
            paper = await asyncio.to_thread(db_handler.get_paper_by_id, paper_id)
            if paper:
                papers.append(paper)
        
        if not papers:
            raise HTTPException(
                status_code=404, 
                detail="No valid papers found for future work generation"
            )

        # Generate future work ideas
        future_work = await future_works_agent.generate_future_work_ideas(papers)
        return future_work

    except HTTPException as he:
        logger.error(f"Future work error: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Future work error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/improvement_plan")
async def improvement_plan(request: ImprovementPlanRequest):
    """
    Endpoint to create an improvement plan based on selected papers.
    """
    try:
        # Retrieve full paper details from the database
        papers = []
        for paper_id in request.paper_ids:
            paper = await asyncio.to_thread(db_handler.get_paper_by_id, paper_id)
            if paper:
                papers.append(paper)
        
        if not papers:
            raise HTTPException(
                status_code=404, 
                detail="No valid papers found for improvement plan creation"
            )

        # Create improvement plan
        improvement_plan = await future_works_agent.create_improvement_plan(papers)
        return improvement_plan

    except HTTPException as he:
        logger.error(f"Improvement plan error: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Improvement plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/review")
async def review_papers(request: ReviewRequest):
    """
    Endpoint to generate a comprehensive review based on selected papers.
    """
    try:
        # Validate request data
        if not request.paper:
            raise HTTPException(
                status_code=422,
                detail="paper_ids are required for review"
            )

        # Retrieve full paper details from the database
        papers = request.paper  # Assuming 'paper' is a list of paper dictionaries

        if not papers:
            raise HTTPException(
                status_code=422,
                detail="No valid papers found for the provided paper_ids"
            )

        # Proceed with generating the review
        review_data = await future_works_agent.create_improvement_plan(papers)

        # Ensure that 'findings' and 'metrics' are included in the response
        return {
            "review": review_data.get("improvement_plan", ""),
            "findings": review_data.get("findings", []),
            "metrics": review_data.get("metrics", {})
        }

    except HTTPException as http_exc:
        logger.error(f"Review endpoint error: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Review endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
