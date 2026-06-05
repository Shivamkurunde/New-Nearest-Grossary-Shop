import os
from pymongo import MongoClient

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://dbRurik:Rutik123@cluster0.dfeobzy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
_client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=50000)
db = _client.grocery_app
