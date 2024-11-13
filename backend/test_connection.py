# test_connection.py
from database.neo4j_handler import Neo4jHandler

def test_connection():
    db = Neo4jHandler()
    try:
        # Run simple query
        with db.driver.session() as session:
            result = session.run("RETURN 1")
            assert result.single()[0] == 1
            print("Connection successful!")
    finally:
        db.close()

if __name__ == "__main__":
    test_connection()