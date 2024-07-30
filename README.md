
# Clash Royale Data Analysis

This project aims to store and analyze battle data from the game Clash Royale in a NoSQL database (MongoDB Atlas) to facilitate analytical queries that allow the analysis of victory/defeat statistics associated with the use of cards, with the goal of balancing the game.

## Project Setup

### Requirements

- Python 3.10
- Anaconda
- MongoDB Atlas account
- Clash Royale API access

### Setup Instructions

1. **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2. **Create a virtual environment using Anaconda:**
    ```bash
    conda create --name clash-royale python=3.10
    conda activate clash-royale
    ```

3. **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables:**
    - Create a `.env` file in the root of your project directory and add your MongoDB URI:
    ```plaintext
    API_KEY="YOUR KEY"
    MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>/clash_royale?retryWrites=true&w=majority
    ```

5. **Run the Flask application:**
    ```bash
    python app.py
    ```

6. **Access the application:**
    - Open your web browser and go to `http://localhost:5000` to access the interface.

## Project Structure

- `app.py`: Main application file containing the Flask routes and functions to handle the queries.
- `collect_data.py`: Script to collect data from the Clash Royale API and store it in MongoDB Atlas.
- `templates/`: Directory containing the HTML templates for the Flask application.
  - `index.html`: Main page with forms to submit queries.
  - `results.html`: Page to display the results of the queries.
- `.env`: File containing environment variables (not included in the repository).

## Queries Implemented

1. **Victory and Defeat Percentage Using Card:**
   - Calculates the percentage of victories and defeats using a specified card within a given time interval.
   - Parameters: card name, start date, end date.

2. **Decks with High Win Percentage:**
   - Lists decks that produced more than a specified percentage of victories within a given time interval.
   - Parameters: minimum win percentage, start date, end date.

3. **Defeats Using Card Combo:**
   - Calculates the number of defeats using a specified combo of cards within a given time interval.
   - Parameters: card combo (comma-separated), start date, end date.

4. **Specific Victory Conditions:**
   - Calculates the number of victories involving a specified card under specific conditions: the winner has a lower percentage of trophies than the loser, the match lasted less than 2 minutes, and the loser destroyed at least two towers.
   - Parameters: card name, trophy difference percentage, start date, end date.

5. **Card Combos with High Win Percentage:**
   - Lists card combos of a specified size that produced more than a specified percentage of victories within a given time interval.
   - Parameters: combo size, minimum win percentage, start date, end date.

## Example Usage

1. **Start the application:**
    ```bash
    python app.py
    ```

2. **Open the web interface:**
    - Navigate to `http://localhost:5000` in your web browser.

3. **Submit queries:**
    - Fill in the forms on the main page with the appropriate parameters and submit to view the results.

## Author

- Pedro Natanael

## License

This project is licensed under the MIT License.
