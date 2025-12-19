import streamlit as st
import pandas as pd

# Load Excel
df = pd.read_csv(r"Extremity_medical-04042021-C1_reviews&ratings.csv")

# Streamlit App Title
st.title("Product Discription, Review and Rating")

# Loop through rows and display each product in a card-like format
for idx, row in df.iterrows():
    with st.container():
        st.subheader(f"🛒 {row['product_name_displayed']}")
        
        # Show description
        st.markdown(
            f"""
            <div style="padding:10px; border-radius:10px; background-color:#9e9e9e; margin-bottom:10px;">
                <b>Description:</b><br>{row['description']}
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Show AI Review
        st.markdown(
            f"""
            <div style="padding:10px; border-radius:10px; background-color:#9e9e9e; margin-bottom:20px;">
                <b>AI Review:</b><br>{row['AI_review']}<br>
                <b>Rating:</b><br>{row['AI_rating']}
            </div>
            """,
            unsafe_allow_html=True
        )
