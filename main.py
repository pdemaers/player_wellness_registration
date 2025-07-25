import logging
from typing import Dict, List, Optional, Union
import streamlit as st
from pymongo import MongoClient, errors
from pymongo.collection import Collection
from datetime import datetime
import calendar
import pandas as pd

# ----------------------------
# Configuration and Constants
# ----------------------------

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# Database Connection Helpers
# ----------------------------

# Connect to MongoDB with error handling
def connect_to_mongodb(collection_name: str) -> Optional[Collection]:
    """
    Establishes a secure connection to a MongoDB collection using Streamlit's Secrets Manager.

    Args:
        collection_name: The name of the MongoDB collection to connect to.

    Returns:
        A reference to the specified MongoDB collection if successful, None otherwise.

    Raises:
        KeyError: If required secrets are missing from Streamlit's configuration.
        ServerSelectionTimeoutError: If connection to MongoDB times out.
        Exception: For other unexpected connection errors.
    """
    try:
        # Validate secrets exist before attempting connection
        required_secrets = ["mongo_username", "mongo_password", "mongo_cluster_url", "database_name"]
        for secret in required_secrets:
            if secret not in st.secrets["MongoDB"]:
                raise KeyError(f"Missing required secret: {secret}")

        # Build connection string from secrets
        username = st.secrets["MongoDB"]["mongo_username"]
        password = st.secrets["MongoDB"]["mongo_password"]
        cluster_url = st.secrets["MongoDB"]["mongo_cluster_url"]
        database_name = st.secrets["MongoDB"]["database_name"]

        connection_string = f"mongodb+srv://{username}:{password}@{cluster_url}/"
        
        # Attempt connection with timeout
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.server_info()  # Test connection
        
        db = client[database_name]
        logger.info(f"Successfully connected to MongoDB collection: {collection_name}")
        return db[collection_name]
    
    except KeyError as e:
        error_msg = f"Missing MongoDB configuration in Streamlit secrets: {e}"
        logger.error(error_msg)
        st.error(error_msg)
    except errors.ServerSelectionTimeoutError:
        error_msg = "Unable to connect to MongoDB server. Please check your internet connection or credentials."
        logger.error(error_msg)
        st.error(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error connecting to MongoDB: {e}"
        logger.error(error_msg, exc_info=True)
        st.error("An unexpected error occurred while connecting to the database.")

    return None

# Insert data into a MongoDB collection
def insert_data(collection_name: str, data: dict) -> bool:
    """
    Inserts a single document into a specified MongoDB collection with validation and error handling.

    Args:
        collection_name: Name of the MongoDB collection to insert into
        data: Dictionary containing the document to be inserted. Must be valid BSON.

    Returns:
        bool: True if insertion was successful, False if insertion failed but was handled gracefully

    Raises:
        ConnectionError: If connection to MongoDB fails
        ValueError: If input data is empty or invalid
        pymongo.errors.PyMongoError: For MongoDB-specific errors (subclasses include:
            - OperationFailure: MongoDB operation failed
            - DuplicateKeyError: Document with same _id exists
            - InvalidDocument: Invalid document structure
            - BulkWriteError: Batch insertion error

    Examples:
        >>> insert_data("players", {"name": "John", "score": 95})
        True
        
        >>> insert_data(None, {})
        ValueError: Collection name cannot be empty
    """
    # Input validation
    if not collection_name:
        raise ValueError("Collection name cannot be empty")
    if not data or not isinstance(data, dict):
        raise ValueError("Data must be a non-empty dictionary")

    try:
        # Get collection with connection handling
        collection = connect_to_mongodb(collection_name)
        if collection is None:
            raise ConnectionError(f"Failed to connect to collection '{collection_name}'")

        # Insert with write concern
        result = collection.insert_one(
            document=data,
            bypass_document_validation=False  # Ensure schema validation if any
        )
        
        if not result.acknowledged:
            logger.warning(f"Write was not acknowledged for collection {collection_name}")
            return False
            
        logger.info(f"Inserted document with ID {result.inserted_id} into {collection_name}")
        return True

    except errors.DuplicateKeyError as e:
        logger.error(f"Duplicate key error: {e.details}")
        raise errors.DuplicateKeyError(f"Document with this ID already exists in {collection_name}", error=e)
        
    except errors.OperationFailure as e:
        logger.error(f"MongoDB operation failed (code {e.code}): {e.details}")
        raise errors.OperationFailure(f"Database operation failed: {e.details}", code=e.code)
        
    except errors.InvalidDocument as e:
        logger.error(f"Invalid document structure: {str(e)}")
        raise ValueError(f"Invalid document format: {str(e)}") from e
        
    except Exception as e:
        logger.critical(f"Unexpected error during insertion: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to insert data: {str(e)}") from e

def get_player_ids() -> pd.Series:
    """
    Fetches all player IDs from the 'roster' collection.

    Returns:
        A pandas Series containing all player IDs.

    Raises:
        Displays a Streamlit error message if the operation fails.
    """
    try:
        collection = connect_to_mongodb("roster")
        if collection is None:
            raise ConnectionError("Could not connect to MongoDB")
            
        df = pd.DataFrame(list(collection.find()))
        df["player_id"] = df["player_id"].astype(str)
        return df["player_id"]
    except Exception as e:
        error_msg = f"Failed to fetch player IDs: {e}"
        logger.error(error_msg, exc_info=True)
        st.error("Failed to load player data. Please try again later.")
        return pd.Series(dtype='object')  # Return empty Series to prevent app crash

# --------------------------
# UI for pre-training entry
# --------------------------

def pre_training_tab():
    st.header(":material/hotel: Pre-Training Wellness Check")

    # Create two columns
    col1, col2 = st.columns(2)

    # Put one input in each column
    with col1:
        pre_player_id = st.selectbox(":material/badge: Your player ID", options=get_player_ids(), index=None, key="player_wellness")

    with col2:
        pre_date = st.date_input(":material/calendar_month: Select date", value=datetime.today(), format="DD/MM/YYYY", max_value=datetime.today(), key="pre_date")
    
    # Radio buttons with emojis
    st.subheader("How about today?")
    
    pre_option_map = {
    1: ":material/sick: A bit sick",
    2: ":material/sentiment_dissatisfied: Not great",
    3: ":material/sentiment_neutral: Not good, not bad",
    4: ":material/sentiment_satisfied_alt: Feeling good",
    5: ":material/sentiment_very_satisfied: I am buzzing"
    }

    pre_training_feeling = st.pills(
        "How are you currently feeling?",
        options = pre_option_map.keys(),
        format_func=lambda option: pre_option_map[option],
        selection_mode="single",
        default=None
    )

    sleep_hours = st.slider("How many hours did you sleep last night?", min_value=0.0, max_value=12.0, value=8.0, step=0.5)

    if st.button("Submit Pre-Training Entry", icon=":material/save:"):
        entry = {
            "player_id": pre_player_id,
            "date": pre_date.strftime("%Y%m%d"),
            "feeling": pre_training_feeling,
            "sleep_hours": sleep_hours,
            "timestamp": datetime.now()
        }
        if insert_data("player_wellness", entry):
            st.success(":material/check_box: Pre-training data submitted successfully!")

# -------------------------------
# UI for post-training RPE entry
# -------------------------------

def post_training_tab():
    st.header(":material/fitness_center: Post-Training RPE Score")

# Create two columns
    col1, col2 = st.columns(2)

    # Put one input in each column
    with col1:
        post_player_id = st.selectbox(":material/badge: Your player ID", options=get_player_ids(), index=None, key="player_rpe")

    with col2:
        post_date = st.date_input(":material/calendar_month: Select date", value=datetime.today(), format="DD/MM/YYYY", max_value=datetime.today(), key="post_date")
    
    st.subheader("Rate of Perceived Exertion (RPE)")

    # Set default session state
    if "selected_rpe" not in st.session_state:
        st.session_state.selected_rpe = None

    # Display radio buttons with numbers only (1 to 10)
    post_session_rpe = st.radio(
        "How did you feel after the session?",
        options=list(range(1, 11)),
        horizontal=True  
    )

    # Save selection in session state
    st.session_state.selected_rpe = post_session_rpe

    # Number of training minutes
    training_minutes = st.number_input(
        "Training minutes",
        min_value=0,
        max_value=120,
        
    )

    # Save training minutes in session state
    st.session_state.training_minutes = training_minutes

    if st.button("Submit RPE Entry", icon=":material/save:"):
        entry = {
            "post_player_id": post_player_id,
            "post_date": post_date.strftime("%Y-%m-%d"),
            "rpe_score": post_session_rpe,
            "training_minutes": training_minutes,
            "timestamp": datetime.now()
        }
        if insert_data("player_rpe", entry):
            st.success(":material/check_box: RPE data submitted successfully!")

# Display BORG scale descriptions
def borg_scale_tab():
    st.header(":material/directions_run: BORG Scale (RPE 1-10) Explanation")
    st.image("images/BORG_RPE_scale.png")

# Main function to run the app

st.set_page_config(
    page_title="Player Wellness App",
    layout="centered",
    page_icon=":weight_lifter:")

st.title("Player Wellness Registration")

tabs = st.tabs(["Pre-Training", "Post-Training RPE", "BORG Scale Info"])

with tabs[0]:
    pre_training_tab()
with tabs[1]:
    post_training_tab()
with tabs[2]:
    borg_scale_tab()


