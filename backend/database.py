from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017" # Mongo db URL
DB_NAME = "workviser" # Name of the database

client = AsyncIOMotorClient(MONGO_URL) # Connection to MongoDB
db = client[DB_NAME] # selecting the database

users_collection         = db["users"]
tasks_collection         = db["tasks"]
help_requests_collection = db["help_requests"]
ratings_collection       = db["ratings"]

# data ^