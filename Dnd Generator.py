from flask import Flask, request, jsonify, send_from_directory
import google.generativeai as genai
import json
import logging

# Initialize Flask app
app = Flask(__name__, static_folder='.')

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Configure Gemini API
genai.configure(api_key="Your Gemini API Key Here")

@app.route('/generate', methods=['POST'])
def generate_content():
    data = request.json
    logging.debug(f"Request received with data: {data}")

    setting_type = data.get('setting_type', 'forest')
    difficulty_level = data.get('difficulty_level', 'medium')
    number_of_monsters = data.get('number_of_monsters', 3)
    area_level = data.get('area_level', 1)

    
    prompt = (
        f"Act as a skilled D&D dungeon master. Create a {setting_type} setting for a party of adventurers. "
        f"The setting should be appropriate for a {difficulty_level} level campaign, with an area level of {area_level}. "
        f"Adjust the area, monsters, and loot according to the level. Include the following details:\n"
        f"1. A vivid description of the area that matches level {area_level}.\n"
        f"2. A list of {number_of_monsters} monsters with names, stats, and detailed abilities, appropriately scaled for level {area_level}.\n"
        f"3. Detailed loot items with stats the monsters might carry, also scaled for level {area_level}.\n"
        f"Use this JSON schema:\n\n"
        f"    Setting = {{\n"
        f"       'setting_description': str,\n"
        f"       'monsters': list[dict[str, any]],\n"
        f"       'loot': str,\n"
        f"       'level': int\n"
        f"    }}\n\n"
        
        # Few-shot Examples
        f"Example 1:\n"
        f"Input: Generate a D&D area set in a dense forest with a medium difficulty level, and an area level of 5. The area should contain 3 monsters and loot.\n"
        f"Output:\n"
        f"{{\n"
        f"    'setting_description': 'The forest is thick with ancient oak trees whose limbs intertwine to form a canopy, blocking most of the sunlight. The air smells earthy, and the ground is soft with moss. Deep in the forest, the sounds of birds and distant creatures create an eerie atmosphere that masks lurking dangers.',\n"
        f"    'monsters': [\n"
        f"        {{\n"
        f"            'name': 'Woodland Goblin',\n"
        f"            'stats': {{\n"
        f"                'Armor Class': 13,\n"
        f"                'Hit Points': 27,\n"
        f"                'Strength': 12,\n"
        f"                'Dexterity': 16,\n"
        f"                'Constitution': 10,\n"
        f"                'Intelligence': 8,\n"
        f"                'Wisdom': 14,\n"
        f"                'Charisma': 10\n"
        f"            }},\n"
        f"            'abilities': ['Sneak Attack', 'Poisonous Dart'],\n"
        f"            'description': 'The Woodland Goblin is a small, nimble creature who hides in the shadows. It uses its speed and stealth to surprise unsuspecting adventurers with deadly poison-tipped darts.'\n"
        f"        }}\n"
        f"    ],\n"
        f"    'loot': 'Potion of Healing (restores 2d4+2 HP)',\n"
        f"    'level': 5\n"
        f"}}\n"
        
        f"Example 2:\n"
        f"Input: Generate a D&D area set in a mountainous region with a hard difficulty level, and an area level of 12. The area should contain 4 monsters and loot.\n"
        f"Output:\n"
        f"{{\n"
        f"    'setting_description': 'The rugged mountain range rises sharply against the sky, covered in snow and jagged rocks. The wind howls as it rushes through narrow canyons, and the high altitude makes breathing difficult. Dangerous predators stalk these cliffs, preying on any adventurers foolish enough to venture too close.',\n"
        f"    'monsters': [\n"
        f"        {{\n"
        f"            'name': 'Rock Troll',\n"
        f"            'stats': {{\n"
        f"                'Armor Class': 16,\n"
        f"                'Hit Points': 102,\n"
        f"                'Strength': 22,\n"
        f"                'Dexterity': 8,\n"
        f"                'Constitution': 18,\n"
        f"                'Intelligence': 6,\n"
        f"                'Wisdom': 10,\n"
        f"                'Charisma': 8\n"
        f"            }},\n"
        f"            'abilities': ['Stone Skin (Resistant to physical damage)', 'Mighty Roar (Terrifying presence causes fear in nearby creatures)'],\n"
        f"            'description': 'The Rock Troll is a hulking brute, its thick stone-like skin making it incredibly tough. It stands over 10 feet tall and uses its massive strength to crush its enemies. When threatened, it lets out a roar that sends weaker creatures fleeing in terror.'\n"
        f"        }}\n"
        f"    ],\n"
        f"    'loot': 'Gold Coins (50), Potion of Fire Resistance',\n"
        f"    'level': 12\n"
        f"}}\n"
    
        f"Return: Setting"
    )


    try:
        logging.debug("Sending prompt to Gemini API...")

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        logging.debug(f"Raw response from Gemini API: {response}")

        # Check if response contains candidates
        if not hasattr(response, 'candidates') or not response.candidates:
            raise ValueError("No valid candidates found in the API response.")

        raw_content = response.candidates[0].content.parts[0].text
        logging.debug(f"Raw content received: {raw_content}")

        # Extract JSON block
        json_block = raw_content.split("```json")[-1].split("```")[0].strip()

        # If no JSON block was found, log an error
        if not json_block:
            raise ValueError("No JSON block found in the response content.")

        logging.debug(f"Extracted JSON block: {json_block}")

        # Parse the JSON block
        try:
            parsed_data = json.loads(json_block)
            logging.debug(f"Parsed data: {parsed_data}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {str(e)}")
            return jsonify({"error": "Failed to parse JSON from model response", "details": str(e)}), 500

        # Check that all required keys are in the parsed data
        required_keys = ['setting_description', 'monsters', 'loot', 'level']
        for key in required_keys:
            if key not in parsed_data:
                logging.error(f"Missing required key: {key}")
                return jsonify({"error": f"Missing required key: {key} in response"}), 500

        # Return the parsed data
        return jsonify(parsed_data)

    except ValueError as ve:
        logging.error(f"ValueError: {str(ve)}")
        return jsonify({"error": "Invalid response from Gemini API", "details": str(ve)}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'Frontend Dnd Generator Monster Sections.html')

if __name__ == '__main__':
    app.run(debug=True)
