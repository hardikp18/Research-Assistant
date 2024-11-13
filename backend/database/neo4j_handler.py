from neo4j import GraphDatabase
from neo4j import Session, Transaction
import logging
from models.schemas import Paper
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator

logger = logging.getLogger(__name__)

class Neo4jHandler:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self._connect()

    def _connect(self):
        """Initialize database connection"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def store_paper(self, paper: Paper) -> bool:
        """
        Store paper and its relationships in Neo4j asynchronously
        """
        try:
            # Since Neo4j Python driver doesn't support native async,
            # we'll use run_in_executor to prevent blocking
            return await self._run_in_executor(self._sync_store_paper, paper)
        except Exception as e:
            logger.error(f"Error storing paper {paper.id}: {e}")
            return False

    async def _run_in_executor(self, func, *args):
        """Helper method to run synchronous code in executor"""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    def _sync_store_paper(self, paper: Paper) -> bool:
        """Synchronous method for storing the paper"""
        with self.get_session() as session:
            return session.execute_write(self._create_paper_tx, paper)

    def _create_paper_tx(self, tx: Transaction, paper: Paper) -> bool:
        """Transaction to create paper with relationships"""
        query = """
        MERGE (p:Paper {id: $id})
        SET p.title = $title,
            p.abstract = $abstract,
            p.year = $year,
            p.url = $url,
            p.full_text = $full_text,
            p.updated_at = datetime()
        
        WITH p
        UNWIND $authors as author
        MERGE (a:Author {name: author})
        MERGE (a)-[:AUTHORED]->(p)
        
        WITH p
        UNWIND $keywords as keyword
        MERGE (k:Keyword {name: keyword})
        MERGE (p)-[:HAS_KEYWORD]->(k)
        
        WITH p
        UNWIND $images as image
        MERGE (i:Image {
            page: image.page,
            index: image.index,
            type: image.type
        })
        MERGE (p)-[:HAS_IMAGE]->(i)
        
        RETURN p
        """
        try:
            result = tx.run(
                query,
                id=paper.id,
                title=paper.title,
                abstract=paper.abstract,
                year=paper.year,
                url=paper.url,
                full_text=getattr(paper, 'full_text', None),
                authors=paper.authors,
                keywords=getattr(paper, 'keywords', []),
                images=getattr(paper, 'images', [])
            )
            return result.single() is not None
        except Exception as e:
            logger.error(f"Transaction error for paper {paper.id}: {e}")
            return False

    async def get_paper_by_id(self, paper_id):
        query = """
        MATCH (p:Paper {id: $id})
        OPTIONAL MATCH (p)-[:HAS_IMAGE]->(i:Image)
        RETURN p, collect(i) as images
        """
        async with self.driver.session() as session:
            try:
                result = await session.execute_run(query, id=paper_id)
                record = await result.single()
                if record:
                    paper = record['p']
                    images = record['images']
                    return {
                        "id": paper.get("id"),
                        "title": paper.get("title"),
                        "images": images
                    }
                return None
            except Exception as e:
                logger.error(f"Error fetching paper by id {paper_id}: {e}")
                return None

    def _sync_get_paper_by_id(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous method for retrieving paper by ID"""
        query = """
        MATCH (p:Paper {id: $id})
        OPTIONAL MATCH (p)<-[:AUTHORED]-(a:Author)
        OPTIONAL MATCH (p)-[:HAS_KEYWORD]->(k:Keyword)
        OPTIONAL MATCH (p)-[:HAS_IMAGE]->(i:Image)
        RETURN p,
               collect(DISTINCT a.name) as authors,
               collect(DISTINCT k.name) as keywords,
               collect(DISTINCT i) as images
        """
        with self.get_session() as session:
            result = session.run(query, id=paper_id)
            record = result.single()
            if record:
                paper = record["p"]
                return {
                    "id": paper["id"],
                    "title": paper["title"],
                    "abstract": paper["abstract"],
                    "year": paper["year"],
                    "url": paper["url"],
                    "full_text": paper.get("full_text"),
                    "authors": record["authors"],
                    "keywords": record["keywords"],
                    "images": [dict(img) for img in record["images"]]
                }
        return None

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Session context manager"""
        if not self.driver:
            self._connect()
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    async def close(self):
        """Close database connection asynchronously"""
        if self.driver:
            await self._run_in_executor(self.driver.close)
            self.driver = None