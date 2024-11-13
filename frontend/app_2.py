import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://localhost:8000"

st.title("Academic Research Assistant")

# Search papers
with st.sidebar:
    topic = st.text_input("Research Topic:")
    if st.button("Search Papers"):
        response = requests.post(
            f"{API_URL}/search",
            json={"topic": topic}
        )
        if response.status_code == 200:
            papers = response.json()["papers"]
            st.session_state.papers = papers
        else:
            st.error("Error searching papers")

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["Papers", "Timeline", "Q&A", "Review"])

with tab1:
    if "papers" in st.session_state:
        df = pd.DataFrame(st.session_state.papers)
        st.dataframe(df)

with tab2:
    if "papers" in st.session_state:
        # Create timeline visualization
        timeline_data = pd.DataFrame(st.session_state.papers)
        
        # Convert 'year' to datetime format
        timeline_data['start_date'] = pd.to_datetime(timeline_data['year'], format='%Y')
        
        # Add one month to create 'end_date' (or adjust as needed)
        timeline_data['end_date'] = timeline_data['start_date'] + pd.DateOffset(months=1)
        
        # Plot the timeline
        fig = px.timeline(
            timeline_data,
            x_start='start_date',
            x_end='end_date',
            y='title',
            title="Research Papers Timeline"
        )
        
        # Update layout
        fig.update_layout(
            xaxis=dict(
                tickformat="%Y",
                dtick="M12"
            )
        )
        
        st.plotly_chart(fig)

with tab3:
    if "papers" in st.session_state:
        selected_papers = st.multiselect(
            "Select Papers to Query:",
            options=[(p["id"], p["title"]) for p in st.session_state.papers],
            format_func=lambda x: x[1]
        )
        
        question = st.text_input("Your Question:")
        if st.button("Ask") and selected_papers:
            
            selected_paper_objects = [
            p for p in st.session_state.papers 
            if p["id"] in [paper_id for paper_id, _ in selected_papers]
            ]
            
            
            response = requests.post(
                f"{API_URL}/answer",
                json={
                    "paper": selected_paper_objects,
                    "question": question
                }
            )
            
            
            if response.status_code == 200:
                answer = response.json()
                st.write("### Answer")
                st.write(answer["answer"])  # Corrected key to match the response format
                with st.expander("Sources"):
                    for source in answer["sources"]:
                        st.write(f"**{source['title']}** ({source['year']})")
                        st.write(source["excerpt"])
            else:
                st.error("Error getting answer")

with tab4:
    if "papers" in st.session_state:
        if st.button("Generate Review"):
            paper_ids = [p["id"] for p in st.session_state.papers]
            response = requests.post(
                f"{API_URL}/review",
                json={"papers": paper_ids}
            )
            if response.status_code == 200:
                review = response.json()
                st.write("### Research Review")
                st.write(review["review"])
                st.write("### Improvement Plan")
                st.write(review["improvement_plan"])
                st.write(f"Analysis covers {review['year_range']}")
            else:
                st.error("Error generating review")