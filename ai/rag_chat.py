import os
import numpy as np
import pandas as pd
import streamlit as st
import snowflake.connector

from google import genai
from dotenv import load_dotenv


# ---------------------------------------
# Load environment variables
# ---------------------------------------

load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-3.5-flash-lite"

NEW_REVIEWS = 100
TOK_K = 5

CACHE_FILE = "review_embeddings.parquet"


# ---------------------------------------
# Gemini client
# ---------------------------------------

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ---------------------------------------
# Read reviews from Snowflake
# ---------------------------------------

def read_reviews_from_snowflake():

    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

    query = f"""
        SELECT REVIEW_ID, CITY, RATING, COMMENT
        FROM ZOMATO.STAGING.STG_REVIEWS
        SAMPLE ({NEW_REVIEWS} ROWS)
    """

    cursor = conn.cursor()

    df = cursor.execute(query).fetch_pandas_all()

    cursor.close()
    conn.close()

    df.columns = [
        col.lower()
        for col in df.columns
    ]

    return df


# ---------------------------------------
# Generate Gemini embeddings
# ---------------------------------------

def embed(texts):

    all_embeddings = []

    # Gemini embedding API accepts
    # maximum 100 requests per batch.
    BATCH_SIZE = 100

    for i in range(0, len(texts), BATCH_SIZE):

        batch = texts[i:i + BATCH_SIZE]

        print(
            f"Generating embeddings "
            f"{i + 1}-{i + len(batch)} "
            f"of {len(texts)}..."
        )

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch
        )

        batch_embeddings = [
            embedding.values
            for embedding in response.embeddings
        ]

        all_embeddings.extend(batch_embeddings)

    return all_embeddings


# ---------------------------------------
# Load reviews
# ---------------------------------------

@st.cache_data()
def load_reviews():

    # Use cached embeddings if available
    if os.path.exists(CACHE_FILE):

        print("Loading embeddings from cache...")

        return pd.read_parquet(
            CACHE_FILE
        )

    print("Reading reviews from Snowflake...")

    df = read_reviews_from_snowflake()

    print(
        f"Generating embeddings for "
        f"{len(df)} reviews..."
    )

    df["embedding"] = embed(
        df["comment"].tolist()
    )

    df.to_parquet(
        CACHE_FILE
    )

    print(
        f"Saved embeddings to {CACHE_FILE}"
    )

    return df


# ---------------------------------------
# Streamlit UI
# ---------------------------------------

st.title(
    "Chat with your Zomato Reviews"
)

st.caption(
    f"Searching {NEW_REVIEWS} reviews, "
    f"answering with {CHAT_MODEL}"
)


# ---------------------------------------
# Cosine similarity
# ---------------------------------------

def cosine_similarity(
    vec_a,
    vec_b
):

    denominator = (
        np.linalg.norm(vec_a)
        * np.linalg.norm(vec_b)
    )

    if denominator == 0:
        return 0

    return np.dot(
        vec_a,
        vec_b
    ) / denominator


# ---------------------------------------
# Find similar reviews
# ---------------------------------------

def find_similar_reviews(
    question,
    df
):

    # Embed user's question
    question_vector = embed(
        [question]
    )[0]

    scores = []

    for review_vector in df["embedding"]:

        scores.append(
            cosine_similarity(
                question_vector,
                review_vector
            )
        )

    df = df.copy()

    df["score"] = scores

    return df.nlargest(
        TOK_K,
        "score"
    )


# ---------------------------------------
# Ask Gemini using retrieved reviews
# ---------------------------------------

def ask_llm(
    question,
    top_reviews
):

    context = ""

    for _, row in top_reviews.iterrows():

        context += (
            f"({row['city']}, "
            f"{row['rating']} stars) "
            f"{row['comment']}\n"
        )

    system_prompt = """
You are a helpful assistant analyzing
Zomato customer reviews.

Answer ONLY using the customer reviews
provided in the context.

Do not invent information.

Be concise.

If the provided reviews do not contain
enough information to answer the question,
say that the reviews do not provide enough
information.
"""

    user_prompt = f"""
Question:
{question}

Customer Reviews:
{context}
"""

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=[
            system_prompt,
            user_prompt
        ],
        config={
            "temperature": 0.2
        }
    )

    return response.text


# ---------------------------------------
# Load review dataset
# ---------------------------------------

review_df = load_reviews()


# ---------------------------------------
# User question
# ---------------------------------------

question = st.text_input(
    "Ask a question about your reviews:",
    placeholder=(
        "e.g. What are the most common "
        "complaints about delivery?"
    )
)


# ---------------------------------------
# RAG pipeline
# ---------------------------------------

if question:

    # Step 1:
    # Find semantically similar reviews
    top_reviews = find_similar_reviews(
        question,
        review_df
    )

    # Step 2:
    # Give retrieved reviews to Gemini
    answer = ask_llm(
        question,
        top_reviews
    )

    # Step 3:
    # Display answer
    st.markdown(
        "**Answer:**"
    )

    st.write(
        answer
    )

    # Step 4:
    # Show retrieved documents
    with st.expander(
        "Reviews used to build this answer"
    ):

        st.dataframe(
            top_reviews[
                [
                    "city",
                    "rating",
                    "comment"
                ]
            ],
            hide_index=True
        )