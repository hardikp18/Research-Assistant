from typing import List, Dict, Optional
from neo4j import GraphDatabase, Driver, Session
from datetime import datetime
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Paper:
    id: str
    title: str
    authors: List[str]
    summary: str
    year: int
    url: str
    keywords: List[str] = None

class DBAgent:
    def __init__(self, uri: str, user: str, password: str):
        """Initialize database connection"""
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.verify_connectivity()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def verify_connectivity(self):
        """Test database connection"""
        try:
            self.driver.verify_connectivity()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()

    def store_paper(self, paper: Paper) -> bool:
        """Store single paper with relationships"""
        try:
            with self.driver.session() as session:
                return session.execute_write(self._create_paper_tx, paper)
        except Exception as e:
            logger.error(f"Error storing paper {paper.id}: {e}")
            return False

    def _create_paper_tx(self, tx: Session, paper: Paper) -> bool:
        """Transaction to create paper and relationships"""
        query = """
        MERGE (p:Paper {id: $id})
        SET p.title = $title,
            p.summary = $summary,
            p.year = $year,
            p.url = $url,
            p.updated_at = datetime()
        WITH p
        UNWIND $authors as author
        MERGE (a:Author {name: author})
        MERGE (a)-[:AUTHORED]->(p)
        WITH p
        UNWIND $keywords as keyword
        MERGE (k:Keyword {name: keyword})
        MERGE (p)-[:HAS_KEYWORD]->(k)
        RETURN p
        """
        result = tx.run(
            query,
            id=paper.id,
            title=paper.title,
            summary=paper.summary,
            year=paper.year,
            url=paper.url,
            authors=paper.authors,
            keywords=paper.keywords or []
        )
        return result.single() is not None

    def query_papers(
        self,
        topic: str,
        start_year: int,
        limit: int = 100
    ) -> List[Paper]:
        """Query papers with pagination and sorting"""
        try:
            with self.driver.session() as session:
                return session.execute_read(
                    self._query_papers_tx,
                    topic,
                    start_year,
                    limit
                )
        except Exception as e:
            logger.error(f"Error querying papers: {e}")
            return []

    def _query_papers_tx(
        self,
        tx: Session,
        topic: str,
        start_year: int,
        limit: int
    ) -> List[Paper]:
        """Transaction to query papers"""
        query = """
        MATCH (p:Paper)
        WHERE p.year >= $start_year
        AND (p.title CONTAINS $topic OR p.summary CONTAINS $topic)
        MATCH (a:Author)-[:AUTHORED]->(p)
        MATCH (p)-[:HAS_KEYWORD]->(k)
        RETURN p.id as id,
               p.title as title,
               p.summary as summary,
               p.year as year,
               p.url as url,
               collect(DISTINCT a.name) as authors,
               collect(DISTINCT k.name) as keywords
        ORDER BY p.year DESC
        LIMIT $limit
        """
        results = tx.run(query, topic=topic, start_year=start_year, limit=limit)
        papers = []
        for record in results:
            papers.append(Paper(
                id=record["id"],
                title=record["title"],
                summary=record["summary"],
                year=record["year"],
                url=record["url"],
                authors=record["authors"],
                keywords=record["keywords"]
            ))
        return papers

    def get_related_papers(self, paper_id: str, limit: int = 5) -> List[Paper]:
        """Find papers with similar keywords or authors"""
        try:
            with self.driver.session() as session:
                return session.execute_read(
                    self._get_related_papers_tx,
                    paper_id,
                    limit
                )
        except Exception as e:
            logger.error(f"Error finding related papers: {e}")
            return []

    def _get_related_papers_tx(
        self,
        tx: Session,
        paper_id: str,
        limit: int
    ) -> List[Paper]:
        """Transaction to find related papers"""
        query = """
        MATCH (p:Paper {id: $paper_id})
        MATCH (p)-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(related:Paper)
        WHERE related.id <> $paper_id
        WITH related, count(k) as common_keywords
        ORDER BY common_keywords DESC
        LIMIT $limit
        MATCH (a:Author)-[:AUTHORED]->(related)
        MATCH (related)-[:HAS_KEYWORD]->(k)
        RETURN related.id as id,
               related.title as title,
               related.summary as summary,
               related.year as year,
               related.url as url,
               collect(DISTINCT a.name) as authors,
               collect(DISTINCT k.name) as keywords
        """
        results = tx.run(query, paper_id=paper_id, limit=limit)
        return [Paper(
            id=record["id"],
            title=record["title"],
            summary=record["summary"],
            year=record["year"],
            url=record["url"],
            authors=record["authors"],
            keywords=record["keywords"]
        ) for record in results]