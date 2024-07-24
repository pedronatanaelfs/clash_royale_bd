
# Clash Royale Battle Data Analysis

This project aims to store and analyze battle data from the real-time strategy game Clash Royale using a NoSQL database. The data analysis will help balance the game based on win/loss statistics associated with card usage.

## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Queries](#queries)
- [Running the Web Application](#running-the-web-application)
- [License](#license)

## Project Overview
The goal of this project is to store battle data in a NoSQL database and perform analytical queries to balance the game based on the win/loss statistics of cards used in battles.

## Features
- Fetch player and battle data from Clash Royale API.
- Store data in a MongoDB database.
- Perform analytical queries to generate insights.
- Web application to visualize the results.

## Requirements
- Python 3.12
- Anaconda
- MongoDB (local or MongoDB Atlas)

## Installation

### 1. Clone the Repository
\`\`\`bash
git clone https://github.com/yourusername/clash-royale-analysis.git
cd clash-royale-analysis
\`\`\`

### 2. Create and Activate Conda Environment
\`\`\`bash
conda create --name clash-royale-312 python=3.12
conda activate clash-royale-312
\`\`\`

### 3. Install Dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 4. Configure MongoDB
- Ensure MongoDB is installed and running locally or configure MongoDB Atlas.
- Create a database named \`clash_royale\`.

## Usage

### 1. Collect Data
Edit \`collect_data.py\` to include your Clash Royale API key and player tag.
Run the script to collect player and battle data and store it in MongoDB.

\`\`\`bash
python collect_data.py
\`\`\`

### 2. Perform Queries
Use the \`queries.py\` script to run predefined analytical queries.

### 3. Running the Web Application
Run the Flask web application to visualize the results.

\`\`\`bash
python app.py
\`\`\`

Visit \`http://127.0.0.1:5000/dashboard/\` to view the dashboard.

## Queries
Here are some example queries you can perform:

1. Calculate the percentage of wins and losses using a specific card.
2. List complete decks that produced more than a specified percentage of wins.
3. Calculate the number of losses using specific card combos.
4. Calculate the number of wins involving a specific card under certain conditions.
5. List card combos that produced more than a specified percentage of wins.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
