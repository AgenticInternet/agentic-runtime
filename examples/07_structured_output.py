"""
Structured Output Example
-------------------------
Agent that returns structured, validated responses using Pydantic models.
Good for: Data extraction, API responses, form filling.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

load_dotenv()

from core import build_agent, AgentSpec, CodeActPolicy


# Define structured output schema
class MovieRecommendation(BaseModel):
    """Schema for movie recommendations."""

    title: str = Field(..., description="Movie title")
    year: int = Field(..., description="Release year")
    genre: str = Field(..., description="Primary genre")
    rating: float = Field(..., ge=0, le=10, description="Rating out of 10")
    reason: str = Field(..., description="Why this movie is recommended")


class MovieList(BaseModel):
    """Schema for a list of movie recommendations."""

    query: str = Field(..., description="Original user query")
    recommendations: List[MovieRecommendation] = Field(
        ..., description="List of recommended movies"
    )
    total_count: int = Field(..., description="Number of recommendations")


def main():
    # Create spec with structured output
    # Uses useful model: z-ai/glm-4.7
    spec = AgentSpec(
        name="movie_recommender",
        model_id="z-ai/glm-4.7",
        codeact=CodeActPolicy(enabled=False),
    ).with_output_schema(MovieList)

    agent = build_agent(spec)

    # Get structured response
    response = agent.run(
        "Recommend 3 sci-fi movies from the 2020s that explore AI themes"
    )

    # Response content is now a validated MovieList object
    if response.content:
        content = response.content
        # Handle case where structured output parsing failed (returns string)
        if isinstance(content, str):
            print("Warning: Failed to parse structured output. Raw response:")
            print(content)
        else:
            print("Structured Response:")
            print(f"Query: {content.query}")
            print(f"Total recommendations: {content.total_count}")
            print("\nMovies:")
            for movie in content.recommendations:
                print(f"  - {movie.title} ({movie.year})")
                print(f"    Genre: {movie.genre}, Rating: {movie.rating}/10")
                print(f"    Reason: {movie.reason}")
                print()
    else:
        print("No response received")


if __name__ == "__main__":
    main()
