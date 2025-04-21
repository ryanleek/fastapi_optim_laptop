from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List
from pydantic import BaseModel, Field
from string import Template

import os
import json
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from ortools.linear_solver import pywraplp

from prompts import feat_extract, feat_match, feat_categorize

def extract(client, chat_history):

    feat_ext = Template(EXTRACT).substitute(CONVERSATION=chat_history)

    response = client.chat.completions.create(
            #model = "o1",
            model = "gpt-4.1", 
            messages = [{"role": "user", "content": feat_ext}],
            response_format = {"type": "json_object"},
            #temperature = 0.1
    )
    user_features = json.loads(response.choices[0].message.content)

    print(user_features)

    return user_features

def match(client, user_features):

    wants = [want["name"] for want in user_features["wants"]]
    avoids = [avoid["name"] for avoid in user_features["avoids"]]
    all_features = wants + avoids
    feat_match = Template(MATCH).substitute(USER_PARAMETERS=all_features)

    response = client.chat.completions.create(
            #model = "o1",
            model = "gpt-4.1", 
            messages = [{"role": "user", "content": feat_match}],
            response_format = {"type": "json_object"},
            #temperature = 0.1
    )
    matched_features = json.loads(response.choices[0].message.content)["result"]

    print(matched_features)

    matched_wants, matched_avoids = [], []
    for feature in matched_features:
        if feature["feature"] in wants:
            matched_wants.append(feature["feature_in_db"]["name"])

        if feature["feature"] in avoids:
            matched_avoids.append(feature["feature_in_db"]["name"])

    print(f"wants: {matched_wants} \navoids: {matched_avoids}")

    return matched_wants, matched_avoids

def categorize(client, chat_history, wants, avoids):

    feat_cat = Template(CATEGORIZE).substitute(CONVERSATION=chat_history, WANTS=wants, AVOIDS=avoids)    

    response = client.chat.completions.create(
            #model = "o1",
            model = "gpt-4.1", 
            messages = [{"role": "user", "content": feat_cat}],
            response_format = {"type": "json_object"},
            #temperature = 0.1
    )
    categorized_features = json.loads(response.choices[0].message.content)["result"]

    final_features = []
    for feat in categorized_features:
        if feat["name"] in wants:
            feat["pref"] = 1
            final_features.append(feat)

        if feat["name"] in avoids:
            feat["pref"] = -1
            final_features.append(feat)

    print(final_features)

    return final_features

def min_max_normalize(column):
    return (column - np.min(column)) / (np.max(column) - np.min(column))

def manage_features(solver, x, matrix, final_features, feature_keys, n_laptops):
    objective = 0
    
    for param in final_features:
        feature = param["name"]
        feat_type = param["type"]
        preference = param["pref"]

        feature_index = feature_keys.index(feature)

        if feat_type == "constraint":

            if preference == 1:
                # For each item i, if it's selected (x[i] = 1), it must satisfy the constraint
                for i in range(n_laptops):
                    solver.Add(x[i] <= matrix[i, feature_index])
            else:
                solver.Add(sum(x[i] * matrix[i, feature_index] for i in range(n_laptops)) == 0)

        else:
            objective += preference * sum(x[i] * matrix[i, feature_index] for i in range(n_laptops))

    solver.Maximize(objective)

def solve_sequentially(names, matrix, final_features, feature_keys, num_suggestions=5):

    selected_items = []
    excluded_items = []
    
    for _ in range(num_suggestions):
        # Reset solver for each iteration
        solver = pywraplp.Solver.CreateSolver("SCIP")
        n = len(names)
        x = [solver.BoolVar(f'x[{i}]') for i in range(n)]
        
        # Add constraint to select exactly one item
        solver.Add(sum(x[i] for i in range(n)) == 1)
        
        # Exclude previously selected items
        for idx in excluded_items:
            solver.Add(x[idx] == 0)
            
        # Apply original constraints and objectives
        manage_features(solver, x, matrix, final_features, feature_keys, n)
        
        # Solve
        status = solver.Solve()
        
        if status == pywraplp.Solver.OPTIMAL:
            # Find the selected item
            for i in range(n):
                if x[i].solution_value() == 1:
                    selected_items.append(names[i])
                    excluded_items.append(i)
                    break
        else:
            break
            
    return selected_items



load_dotenv()
client = OpenAI()

EXTRACT = feat_extract
MATCH = feat_match
CATEGORIZE = feat_categorize

# Data import
with open('laptop_vector.json', 'r') as f:
    laptop_vectors = json.load(f)

with open('laptop_data.json', 'r') as f:
    laptop_data = json.load(f)

laptop_names = [vector["name"] for vector in laptop_vectors]
feature_keys = list(laptop_vectors[0]['features'].keys())

# Convert data into numpy array
matrix = np.array([list(vector["features"].values()) for vector in laptop_vectors], dtype=float)
for i in range(58, 68):
    matrix[:, i] = min_max_normalize(matrix[:, i])




app = FastAPI(
    title="Laptop Optimization API",
    description="API for optimizing user parameters and then returns recommend worthy laptops",
    version="1.0.0",
    servers=[
        {
            "url": "https://fastapi-optim-laptop.vercel.app",
            "description": "Local development server, improves user parameter and then performs optimizaiton"
        }
    ]
)

# # Custom middleware to handle ngrok header
# @app.middleware("http")
# async def add_ngrok_header(request: Request, call_next):
#     response = await call_next(request)
#     response.headers["ngrok-skip-browser-warning"] = "true"
#     return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatSummary(BaseModel):
    chat_summary: str = Field(..., title = "Summarized version of user and staff member's conversation")

class Laptop(BaseModel):
    laptop_info: str = Field(..., title="description of informations regarding the laptop")

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    with open("privacy.html", "r") as file:
        return file.read()

@app.get("/optimize", response_model=List[Laptop])
async def optimizer(
    chat_summary: str = Query(..., title="summary of user and staff member's conversation")
) -> list:
    """from user-staff conversation, extracts user features and then returns optimized+ranked laptop recommendation list"""

    features = extract(client, chat_summary)
    wants, avoids = match(client, features)
    final_features = categorize(client, chat_summary, wants, avoids)

    ranked_suggestions = solve_sequentially(laptop_names, matrix, final_features, feature_keys)

    rec_list = []
    for laptop in ranked_suggestions:
        for item in laptop_data:
            if item["name"] == laptop: rec_list.append(item)

    print(rec_list)

    return [Laptop(laptop_info=str(laptop)) for laptop in rec_list]