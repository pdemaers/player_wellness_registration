# ⚽ Player Wellness Registration App

This Streamlit app allows youth soccer players to log their **wellness before training** and **RPE (Rate of Perceived Exertion) after training**. Data is securely stored in a MongoDB database, enabling coaches to monitor player wellbeing and training load over time.

---

## 🔍 Features

- 🛏️ **Pre-Training Wellness Check**
  - Player ID selection
  - Self-assessed feeling score (1–5 scale)
  - Sleep duration input (0–12 hours)

- 💪 **Post-Training RPE Input**
  - RPE score (1–10 scale)
  - Training duration (0–120 minutes)

- 📊 **BORG Scale Visual Guide**
  - Helps players understand the RPE scale with a visual reference

- 🔐 **Secure MongoDB Integration**
  - Credentials managed using `.streamlit/secrets.toml`
  - Data stored in collections: `roster`, `player_wellness`, `player_rpe`

---

## 📦 Requirements

- Python 3.9+
- MongoDB Atlas (or compatible server)
- The following Python packages:

  ```
  streamlit>=1.32.0  
  pymongo>=4.6.0  
  pandas>=2.2.0
  ```

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## 🚀 Running Locally

1. **Clone this repository:**

   ```bash
   git clone https://github.com/yourusername/player-wellness-app.git
   cd player-wellness-app
   ```

2. **(Optional) Create a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Create your Streamlit secrets file:**

   Create a file at `.streamlit/secrets.toml`:

   ```toml
   [MongoDB]
   mongo_username = "your_username"
   mongo_password = "your_password"
   mongo_cluster_url = "your_cluster.mongodb.net"
   database_name = "your_database_name"
   ```

   > ⚠️ This file is excluded from version control via `.gitignore`.

4. **Run the app:**

   ```bash
   streamlit run main.py
   ```

---

## ☁️ Deploying to Streamlit Cloud

1. Push your app to a public or private GitHub repo.
2. Go to [https://share.streamlit.io](https://share.streamlit.io).
3. Create a new app and select your repo and branch.
4. Under the **Secrets** tab in Streamlit Cloud:
   - Add the same `[MongoDB]` values from your `secrets.toml`.

---

## 🗃️ MongoDB Collections

This app expects the following MongoDB collections:

### `roster`
- Stores player metadata.
- Must contain a field `player_id` (used in dropdowns).

### `player_wellness`
- Stores daily pre-training wellness input:
  - `player_id`, `date`, `feeling`, `sleep_hours`, `timestamp`

### `player_rpe`
- Stores daily post-training RPE input:
  - `post_player_id`, `post_date`, `rpe_score`, `training_minutes`, `timestamp`

---

## 🧠 BORG Scale Reference

The app includes a tab that displays an image explaining the RPE scale from 1 to 10.  
Make sure this file exists in your project:

```
images/BORG_RPE_scale.png
```

If you don’t have the image, you can find BORG RPE scale charts online or create your own.

---

## 📁 Project Structure

```
player-wellness-app/
├── main.py                  # Main Streamlit app
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
├── .gitignore               # Git ignored files (includes .venv and secrets)
├── .streamlit/
│   └── secrets.toml         # MongoDB credentials (excluded from Git)
└── images/
    └── BORG_RPE_scale.png   # RPE chart image
```

---

## 👤 Author

Developed by [Your Name / Club Name]  
For feedback or questions: [your-email@example.com]

---

## 🛡️ License

This project is open-source under the [MIT License](LICENSE), unless otherwise specified.
