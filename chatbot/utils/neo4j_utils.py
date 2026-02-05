# chatbot/utils/neo4j_utils.py
from neo4j import GraphDatabase
import utils.config

# Utility class to manage neo4j databases
class Neo4jManager:

    def __init__(self, neo4j_uri = "bolt://127.0.0.1:7687", neo4j_auth = ("neo4j", "neo4j")):
        self.neo4j_available = False
        self.driver = None
        self.local_storage = {}  # Fallback local

        self.init_neo4j(neo4j_uri, neo4j_auth)

    def init_neo4j(self, neo4j_uri, neo4j_auth):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)
        try:
            self.driver.verify_connectivity()
            self.neo4j_available = True
        except Exception as e:
            print(f"Exception raised connecting to Neo4j: {e}")

    def _check_fulltext_index(self, index_name = "test_index", labels = ["test_node"], props = ["name"]):
        print("XXX GREEDY HOG XXX")
        query = f"""
            CREATE FULLTEXT INDEX `{index_name}` IF NOT EXISTS
            FOR (n:{'|'.join(labels)}) ON EACH [n.{', n.'.join(props)}]
        """
        return self.execute_query(query)

    def _fulltext_query(self, index_name, query):
        query = f"""
            CALL db.index.fulltext.queryNodes(`{index_name}`, {query})
            YIELD node, score
            RETURN node, score
            ORDER BY score DESC
        """
        return self.driver.execute_query(query)


    def execute_query(self, query, params={}):
        if not self.neo4j_available:
            logging.warning("Neo4j not available.  Returning empty result.")
            return []
        try:
            if utils.config.verbose:
                utils.config.debug_print(f"[NEO4J] Sending query {query} with params {params}")
            with self.driver.session() as session:
                result = session.run(query, **params)
                if utils.config.verbose:
                    utils.config.debug_print(f"[NEO4J] Executed query {result.data()}")
                return result.data()
        except Exception as e:
            logging.error(f"Error executing query: {e}")
            return []

    def _add_params(self, params={}, prefix=""):
        # A way to handle arbitrary params
        if len(prefix) > 0:
            if prefix[-1] != "_":
                prefix += "_"
        conditions = []
        keys = list(params.keys())
        values = list(params.values())
        for key, value in zip(keys, values):
            if key[0] != "_":
                params[f"{prefix}{key}"] = value
                conditions.append(f"{key}: ${prefix}{key}")
        return f"{{{', '.join(conditions)}}}"

    def set_node(self, node_type, params={}):
        query = f"MERGE (d: $($node_type) {self._add_params(params)}) RETURN d\n"
        params["node_type"] = node_type
        return self.execute_query(query, params)

    def get_node(self, node_type, params={}):
        query = f"MATCH (d: $($node_type) {self._add_params(params)}) RETURN d\n"
        params["node_type"] = node_type
        return self.execute_query(query, params)

    def del_node(self, node_type, params={}):
        query = f"MATCH (d: $($node_type) {self._add_params(params)}) DETACH DELETE d\n"
        params["node_type"] = node_type
        return self.execute_query(query, params)

    def set_relation(self, node1_type, node2_type, relation,
                     node1_params={}, node2_params={}, relation_params={}):
        query = f"MATCH (d1: $($node1_type) {self._add_params(node1_params, 'node1')}), "
        query += f"(d2: $($node2_type) {self._add_params(node2_params, 'node2')}) "
        query += f"CREATE (d1)-[r:$($relation) {self._add_params(relation_params)}]->(d2) RETURN r\n"
        params = {"node1_type": node1_type,
                  "node2_type": node2_type,
                  "relation": relation,
                  **node1_params, **node2_params, **relation_params}
        return self.execute_query(query, params)

    def get_relation(self, node1_type, node2_type, relation,
                     node1_params={}, node2_params={}, relation_params={}):
        query = f"MATCH (d1: $($node1_type) {self._add_params(node1_params, 'node1')}), "
        query += f"(d2: $($node2_type) {self._add_params(node2_params, 'node2')}) "
        query += f"MATCH (d1)-[r:$($relation) {self._add_params(relation_params)}]->(d2) RETURN r\n"
        params = {"node1_type": node1_type,
                  "node2_type": node2_type,
                  "relation": relation,
                  **node1_params, **node2_params, **relation_params}
        return self.execute_query(query, params)


