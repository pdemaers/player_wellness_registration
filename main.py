"""Player Wellness Registration App

A multi-tab Streamlit app for managing player wellness, training sessions, and RPE data. Built for use by coaching staff with data stored in MongoDB.
"""

import logging
from typing import Dict, List, Optional, Union
import streamlit as st
from pymongo import MongoClient, errors
from pymongo.collection import Collection
from datetime import datetime
import calendar
import pandas as pd
import numpy as np

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
    """
    Displays the Pre-Training Wellness Check form in the Streamlit application.

    This form allows players to submit their wellness status before a training session,
    including how they feel, how many hours they slept, and the date of entry. The
    submitted data is stored in the 'player_wellness' MongoDB collection.

    Args:
        None

    Returns:
        None

    Side Effects:
        Renders Streamlit UI components including selectbox, date input, radio buttons, 
        slider, and a submit button.
        Submits a document to the 'player_wellness' collection in MongoDB upon form submission.

    Data Submitted:
        player_id (str): Selected player ID from the dropdown.
        date (str): Selected date, formatted as 'YYYYMMDD'.
        feeling (int): A rating from 1 (sick) to 5 (buzzing), selected via pill-style buttons.
        sleep_hours (float): Number of hours slept, between 0.0 and 12.0.
        timestamp (datetime): The exact moment the form was submitted.

    Raises:
        None
    """
    st.header(":material/hotel: Pre-Training Wellness Check")

    # Create two columns
    col1, col2 = st.columns(2)

    # Put one input in each column
    with col1:
        pre_player_id = st.selectbox(":material/badge: Your player ID", options=get_player_ids(), index=None, key="player_wellness")

    with col2:
        pre_date = st.date_input(":material/calendar_month: Select date", value=datetime.today(), format="DD/MM/YYYY", max_value=datetime.today(), key="pre_date")
    
    session_id = f"{pre_date.strftime('%Y%m%d')}U{str(pre_player_id)[:2]}"
    st.session_state.session_id = session_id

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
            "player_id": int(pre_player_id),
            "session_id": session_id,
            "date": datetime.combine(pre_date, datetime.min.time()).isoformat(),
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
    """
    Displays the Post-Training RPE Score form in the Streamlit application.

    This form allows players to submit their perceived exertion score after a training session,
    along with the duration of the session and the date. The submitted data is stored in the
    'player_rpe' MongoDB collection.

    Args:
        None

    Returns:
        None

    Side Effects:
        Renders Streamlit UI components including selectbox, date input, radio buttons, 
        number input, toggle, and a submit button.
        Stores user input in `st.session_state` for selected RPE score and training minutes.
        Submits a document to the 'player_rpe' collection in MongoDB upon form submission.

    Data Submitted:
        post_player_id (str): Selected player ID from the dropdown.
        post_date (str): Selected date, formatted as 'YYYY-MM-DD'.
        rpe_score (int): Perceived exertion score from 1 (very light) to 10 (maximum effort).
        training_minutes (int): Duration of the session in minutes (0 to 120).
        individual_session (bool): Indication if the players did an individual training session.
        timestamp (datetime): The exact moment the form was submitted.

    Raises:
        None
    """
    st.header(":material/fitness_center: Post-Training RPE Score")

    # Create two columns
    col1, col2 = st.columns(2)

    # Put one input in each column
    with col1:
        post_player_id = st.selectbox(":material/badge: Your player ID", options=get_player_ids(), index=None, key="player_rpe")

    with col2:
        post_date = st.date_input(":material/calendar_month: Select date", value=datetime.today(), format="DD/MM/YYYY", max_value=datetime.today(), key="post_date")
    
    session_id = f"{post_date.strftime('%Y%m%d')}U{str(post_player_id)[:2]}"
    st.session_state.session_id = session_id

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

    # Individual session registration
    individual_session = st.toggle("Individual session", value=False)

    # Save the individual session in session state
    st.session_state.individual_session = individual_session

    if st.button("Submit RPE Entry", icon=":material/save:"):
        entry = {
            "player_id": np.int32(post_player_id),
            "session_id": session_id,
            "date": datetime.combine(post_date, datetime.min.time()).isoformat(),
            "rpe_score": post_session_rpe,
            "training_minutes": training_minutes,
            "individual_session": individual_session,
            "timestamp": datetime.now()
        }
        if insert_data("player_rpe", entry):
            st.success(":material/check_box: RPE data submitted successfully!!")

# Display BORG scale descriptions
def borg_scale_tab():
    """
    Displays the BORG Scale (RPE 1–10) explanation tab in the Streamlit application.

    This tab provides a visual reference for players to better understand how to rate their
    perceived exertion after training sessions, based on the BORG RPE scale.

    Args:
        None

    Returns:
        None

    Side Effects:
        Renders a header and displays an explanatory image of the BORG RPE scale.

    Raises:
        None
    """    
    st.header(":material/directions_run: BORG Scale (RPE 1-10) Explanation")
    st.image("images/BORG_RPE_scale.png")

# Main function to run the app

def main():
    """
    Initializes and runs the Streamlit Player Wellness App.

    This function sets up the page configuration and renders the main navigation tabs:
    - Pre-Training Wellness Check
    - Post-Training RPE Score
    - BORG Scale (RPE) Explanation

    Each tab is linked to its corresponding function that manages the form input and UI rendering.

    Args:
        None

    Returns:
        None

    Side Effects:
        Sets the Streamlit page configuration.
        Renders the app UI including title and tab layout.
        Calls tab-specific functions to handle data input and visualization.

    Raises:
        None
    """
    st.set_page_config(
        page_title="Player Wellness App",
        page_icon="🏋️‍♂️",
        layout="centered"
    )

    st.title("Player Wellness Registration")

    tabs = st.tabs(["Pre-Training", "Post-Training RPE", "BORG Scale Info"])

    with tabs[0]:
        pre_training_tab()
    with tabs[1]:
        post_training_tab()
    with tabs[2]:
        borg_scale_tab()

if __name__ == "__main__":
    main()
