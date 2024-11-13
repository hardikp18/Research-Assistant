import streamlit as st
import requests
import pandas as pd
import re
import logging
from typing import Dict

API_URL = "http://localhost:8000"

st.title("Academic Research Assistant")

logger = logging.getLogger(__name__)

# Initialize session states
if "messages" not in st.session_state:
    st.session_state.messages = []
if "papers" not in st.session_state:
    st.session_state.papers = []
if "papers_df" not in st.session_state:
    st.session_state.papers_df = None
if 'selected_papers' not in st.session_state:
    st.session_state.selected_papers = []

def detect_intent(message: str) -> str:
    """Detect user intent from message"""
    message = message.lower()
    if any(x in message for x in ["search", "show", "papers"]):
        return "search"
    elif any(x in message for x in ["explain", "what", "how", "why", "describe"]):
        return "qa"
    elif any(x in message for x in ["review", "summarize", "summary"]):
        return "review"
    elif any(x in message for x in ["future", "improvements", "suggestions"]):
        return "future_works"
    return "qa"  # default to QA

# def format_review(review: Dict) -> tuple:
#     """Format review as DataFrames"""
#     # Main findings DataFrame
#     findings_df = pd.DataFrame({
#         'Category': ['Time Period', 'Key Findings', 'Future Directions'],
#         'Content': [
#             review.get('year_range', ''),
#             review.get('review', ''),
#             review.get('improvement_plan', '')
#         ]
#     })

#     # Metrics DataFrame
#     metrics_df = pd.DataFrame({
#         'Metric': ['Papers Analyzed', 'Year Range', 'Topics Covered'],
#         'Value': [
#             review.get('paper_count', 0),
#             review.get('year_range', ''),
#             len(review.get('topics', []))
#         ]
#     })

#     return findings_df, metrics_df

def process_message(user_message: str) -> str:
    """Process user message and return assistant's response"""
    intent = detect_intent(user_message)

    try:
        if intent == "search":
            topic_match = re.search(r"(?:about|related to|papers on|find)\s+(.+?)(?:\s+in|\?|$)", user_message)
            topic = topic_match.group(1) if topic_match else user_message

            response = requests.post(f"{API_URL}/search", json={"topic": topic})
            if response.status_code == 200:
                papers = response.json()["papers"]
                count = response.json()["count"]
                st.session_state.papers = papers
                st.session_state.selected_papers = []

                # Convert to DataFrame
                df = pd.DataFrame([{
                    'Title': p['title'],
                    'Year': p['year'],
                    'Authors': ', '.join(p['authors']),
                    'Abstract': p['abstract'][:200] + '...'
                } for p in papers])

                st.session_state.papers_df = df

                return f"🔍 Found {count} papers on '{topic}'"
            else:
                return "❌ Error fetching papers"

        elif intent == "qa":
            if not st.session_state.selected_papers:
                return "⚠️ Please select papers to use for Q&A!"

            response = requests.post(
                f"{API_URL}/answer",
                json={
                    "paper": st.session_state.selected_papers,
                    "question": user_message
                }
            )

            if response.status_code == 200:
                answer_data = response.json()
                if answer_data and 'answer' in answer_data:
                    # Build the response string
                    response_text = f"### Answer\n{answer_data['answer']}\n\n"
                    response_text += f"**Confidence:** {answer_data.get('confidence', 0):.2%}\n\n"

                    if answer_data.get('sources'):
                        response_text += "### Sources\n"
                        for source in answer_data['sources']:
                            response_text += f"- **{source['title']}** ({source['year']})\n"
                            response_text += f"  Excerpt: {source['excerpt']}\n"

                    return response_text
                else:
                    return "❌ No answer received"
            else:
                return f"❌ Error: Server returned status {response.status_code}"

        elif intent in ["review", "future_works"]:
            if not st.session_state.selected_papers:
                return "⚠️ Please select papers first!"

            response = requests.post(
                f"{API_URL}/review",
                json={"paper": st.session_state.selected_papers}
            )
            if response.status_code == 200:
                review_data = response.json()

                review_text = f"### Research Review\n\n{review_data['review']}\n\n"

                return review_text
            else:
                return f"❌ Error fetching review"

    except Exception as e:
        return f"❌ Error: {str(e)}"

    return "❓ I'm not sure how to help with that. Try asking about papers or specific questions!"

# Display chat interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Main input for user messages
if prompt := st.chat_input("Ask me about research papers..."):
    # Append user's message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process the message and get the response
    response = process_message(prompt)

    # Append assistant's response
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)

# Display search results and multiselect in the sidebar
if st.session_state.papers:
    with st.sidebar:
        st.write("### Search Results")
        st.dataframe(st.session_state.papers_df, use_container_width=True)

        # Create a dictionary mapping paper IDs to titles
        paper_dict = {p["id"]: p["title"] for p in st.session_state.papers}

        # Display the multiselect widget
        selected_paper_ids = st.multiselect(
            "Select Papers to Use:",
            options=list(paper_dict.keys()),
            format_func=lambda x: paper_dict[x],
            default=[p["id"] for p in st.session_state.selected_papers]
        )

        # Update selected papers in session state
        st.session_state.selected_papers = [
            p for p in st.session_state.papers if p["id"] in selected_paper_ids
        ]

        # Optionally, display the selected papers
        if st.session_state.selected_papers:
            st.write("### Selected Papers for Q&A")
            selected_df = pd.DataFrame([{
                'Title': p['title'],
                'Authors': ', '.join(p['authors']),
                'Year': p['year'],
            } for p in st.session_state.selected_papers])
            st.dataframe(selected_df, use_container_width=True)