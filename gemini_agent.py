import json
import logging
import os
import hashlib
import random
from google import genai
from google.genai import types
from app import db
from models import ResponseHistory

# This API key is from Gemini Developer API Key, not vertex AI API Key
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_response_hash(response_text):
    """Generate a hash for response uniqueness checking"""
    return hashlib.sha256(response_text.encode()).hexdigest()

def is_response_unique(response_text):
    """Check if the response has been used before"""
    response_hash = generate_response_hash(response_text)
    existing = ResponseHistory.query.filter_by(response_hash=response_hash).first()
    return existing is None

def save_response_hash(response_text):
    """Save response hash to prevent future duplicates"""
    response_hash = generate_response_hash(response_text)
    history_entry = ResponseHistory(response_hash=response_hash)
    db.session.add(history_entry)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving response hash: {e}")

def generate_funny_response(username, food_type, vote_id):
    """
    Generate a unique, funny response for a food vote using Gemini LLM.
    Mentions the vote ID and food choice.
    Ensures no repeated responses.
    """
    
    # Define precise prompt templates for 2-3 line funny responses
    prompt_templates = [
        f"Write exactly 2-3 lines of funny commentary for vote ID '{vote_id}' choosing {food_type}. Use food puns and witty observations. Mention the ID '{vote_id}' in your response. Be hilarious but concise!",
        
        f"Create a brief 2-3 line comedic response to vote ID '{vote_id}' selecting {food_type}. Include clever wordplay and food humor. Reference '{vote_id}' in the response. Make it snappy and entertaining!",
        
        f"Generate exactly 2-3 lines of witty, food-themed banter for ID '{vote_id}' choosing {food_type}. Use humor and mention the vote ID '{vote_id}'. Keep it short and punchy!",
        
        f"Write a concise 2-3 line funny reaction to '{vote_id}' voting for {food_type}. Be creative with food jokes and puns. Include the ID '{vote_id}' in your response. Make it memorable but brief!",
        
        f"Create exactly 2-3 lines of playful commentary for vote ID '{vote_id}' selecting {food_type}. Use clever humor and food references. Mention '{vote_id}' in the response. Keep it short and amusing!"
    ]
    
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # Select a random prompt template
            selected_prompt = random.choice(prompt_templates)
            
            # Add randomness factors to the prompt (emphasizing brevity)
            randomness_factors = [
                "Make it extra silly with unexpected comparisons. Maximum 2-3 lines only!",
                "Include a food conspiracy theory joke. Keep it to 2-3 lines maximum!",
                "Add dramatic food critic flair. Strictly 2-3 lines only!",
                "Sound like a sports commentator. Limit to exactly 2-3 lines!",
                "Include a silly food superhero reference. Maximum 2-3 lines!",
                "Add clever rhyming or wordplay. Keep it to 2-3 lines only!",
                "Make it a breaking news report. Strictly 2-3 lines maximum!"
            ]
            
            final_prompt = selected_prompt + " " + random.choice(randomness_factors) + " IMPORTANT: Response must be exactly 2-3 lines, no more!"
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=final_prompt
            )
            
            if response.text:
                response_text = response.text.strip()
                
                # Check if response is unique
                if is_response_unique(response_text):
                    # Save the response hash to prevent future duplicates
                    save_response_hash(response_text)
                    logging.info(f"Generated unique response for vote ID '{vote_id}' choosing {food_type}")
                    return response_text
                else:
                    logging.info(f"Generated duplicate response, retrying... (attempt {attempt + 1})")
                    attempt += 1
            else:
                attempt += 1
                
        except Exception as e:
            logging.error(f"Error generating Gemini response (attempt {attempt + 1}): {e}")
            attempt += 1
    
    # Fallback responses if Gemini fails or all responses are duplicates
    fallback_responses = [
        f"🎉 Vote ID '{vote_id}' has chosen {food_type}! The {food_type} gods smile upon this choice today! 🍕🍔",
        f"Wow '{vote_id}'! Team {food_type} just got stronger! This ID has excellent judgment! 👨‍🍳✨",
        f"Breaking news: Vote '{vote_id}' has officially declared allegiance to {food_type}! The culinary world rejoices! 📢🎊",
        f"Alert! Vote ID '{vote_id}' for {food_type} has been detected by our flavor sensors! Deliciousness level: Maximum! 🚨😋",
        f"Congratulations '{vote_id}'! You've just made {food_type} history with that vote! Legend status: Activated! 🏆🎯"
    ]
    
    # Select a fallback and ensure it's somewhat unique by adding timestamp info
    import time
    timestamp_suffix = str(int(time.time() * 1000))[-3:]  # Last 3 digits of timestamp
    selected_fallback = random.choice(fallback_responses) + f" (Vote #{timestamp_suffix})"
    
    logging.warning(f"Using fallback response for {username}'s {food_type} vote")
    return selected_fallback
