# backend/agents/search_agent.py

import arxiv
from typing import List, Optional, Dict, Any
from models.schemas import Paper
from database.neo4j_handler import Neo4jHandler
from services.pdf_processing import PDFProcessingService
import logging
import asyncio

logger = logging.getLogger(__name__)

class SearchAgent:
    def __init__(self, db_handler: Neo4jHandler):
        self.db_handler = db_handler
        self.pdf_processor = PDFProcessingService()
        
    async def _store_paper_safe(self, paper: Paper) -> None:
        """Safely store paper with PDF content"""
        try:
            # Extract PDF content using process_pdf_url
            pdf_content: Optional[Dict[str, Any]] = await self.pdf_processor.process_pdf_url(paper.url)
            
            if pdf_content:
                paper.full_text = pdf_content["text"]
                paper.images = pdf_content["images"]
            
            # Store paper in database
            success = await asyncio.to_thread(
                self.db_handler.store_paper,
                paper
            )
            
            if not success:
                logger.warning(f"Failed to store paper {paper.id}")
                
        except Exception as e:
            logger.error(f"Error storing paper with PDF: {e}")
            raise

    async def search_papers(self, topic: str, max_results: int = 5) -> List[Paper]:
        """Search for papers on given topic"""
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=topic,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )

            results = list(client.results(search))[:max_results]
            papers: List[Paper] = []

            for result in results:
                try:
                    # Create paper with required fields
                    paper = Paper(
                        id=result.entry_id.split("/")[-1],
                        title=result.title,
                        authors=[str(author) for author in result.authors],
                        abstract=result.summary,
                        year=result.published.year,
                        url=result.pdf_url,
                        has_full_text=False,  # Will be updated after PDF processing
                        has_images=False      # Will be updated after PDF processing
                    )
                    
                    # Store and process PDF
                    await self._store_paper_safe(paper)
                    papers.append(paper)
                    
                except Exception as e:
                    logger.error(f"Error processing paper {result.entry_id}: {e}")
                    continue

            return papers

        except Exception as e:
            logger.error(f"Search error: {e}")
            raise