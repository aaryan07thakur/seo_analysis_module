from pymongo import MongoClient

# MongoDB connection details

MONGO_URI = "mongodb://localhost:27017/seo_analysis"
# MONGO_URI = "mongodb://db:27017"

# Create MongoDB client
client = MongoClient(MONGO_URI)

# Get the database
db = client["seo_analysis"]