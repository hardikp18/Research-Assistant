# Research-Assistant

## Overview

The Academic Research Assistant is a comprehensive application designed to facilitate academic research by enabling users to search for research papers, generate reviews, perform Q&A based on selected papers, and create reviews. The application leverages FastAPI for the backend, Streamlit for the frontend, and integrates with a Neo4j database and various machine learning models to deliver its features.

## Features

- **Question Answering (QA) Agent:** Provides answers based on the content of academic papers.
- **Search Functionality:** Enables searching through papers using Neo4j.
- **Review Generation:** Compiles comprehensive reviews of selected papers.

## Installation

1. **Clone the Repository:**

    ```bash
    https://github.com/hardikp18/Research-Assistant.git
    cd research-assistant
    ```

2. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Configure Environment Variables:**

    Create a `.env` file in the `backend` directory with the following content:

    ```env
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=your_password
    ```

## Usage

1. **Start the Backend Server:**

    ```bash
    cd backend
    uvicorn main:app --reload
    ```

2. **Start the Frontend Application:**

    ```bash
    cd frontend
    streamlit run app.py
    ```

## Project Structure

- **backend/**
    - **agents/**
        - `qa_agent.py`: Handles question answering functionalities.
        - `search_agent.py`: Manages search operations within the database.
        - `future_works_agent.py`: Generates future work ideas and improvement plans.
        - `db_agent.py`: Defines the `Paper` model.
    - **database/**
        - `neo4j_handler.py`: Handles interactions with the Neo4j database.
    - **models/**
        - `schemas.py`: Defines Pydantic models for request and response schemas.
    - **services/**
        - `pdf_processing.py`: Processes PDF files and extracts relevant data.
    - `config.py`: Configuration settings for the application.
    - `main.py`: Entry point for the FastAPI backend.
- **frontend/**
    - `app.py`: Streamlit application for the user interface.
- `requirements.txt`: Lists all Python dependencies.

## Technologies Used

- **Backend:**
    - Python
    - FastAPI
    - Transformers
    - Torch
    - Neo4j
      
- **Frontend:**
    - Streamlit
    - Python
