#!/usr/bin/env python3
"""
Generate test ghost story data for Bronze layer ETL testing
"""
import asyncio
import asyncpg
import random
from datetime import datetime, timedelta

# Sample ghost story templates
STORY_TEMPLATES = [
    {
        "title": "The Haunted {location}",
        "content": "I never believed in ghosts until I moved into the old {location} on {street_name}. The first night was quiet, but by the third day, I started hearing {sound} coming from the {room}. Every night at exactly {time}, the temperature would drop and I could see my breath. The {object} would move on its own, and sometimes I caught glimpses of a shadowy figure in my peripheral vision. The locals warned me about the history of this place - a {tragedy} had occurred here decades ago. I should have listened to their warnings, but I was too stubborn to believe in the supernatural. That was before I encountered {entity} face to face.",
        "variables": {
            "location": ["Victorian house", "apartment building", "farmhouse", "mansion", "cottage", "cabin"],
            "street_name": ["Elm Street", "Oak Avenue", "Maple Lane", "Pine Road", "Cedar Drive", "Willow Street"],
            "sound": ["footsteps", "whispers", "crying", "scratching", "knocking", "voices"],
            "room": ["attic", "basement", "hallway", "bedroom", "kitchen", "living room"],
            "time": ["3:33 AM", "midnight", "2:15 AM", "11:47 PM", "1:00 AM", "4:44 AM"],
            "object": ["rocking chair", "picture frame", "door", "window", "mirror", "lamp"],
            "tragedy": ["murder", "suicide", "fire", "accident", "disappearance", "illness"],
            "entity": ["the previous owner", "a child spirit", "an old woman", "a shadow figure", "the victim", "an angry spirit"]
        }
    },
    {
        "title": "The {object} in the {room}",
        "content": "My grandmother left me her old {object} when she passed away. I decided to put it in the {room} of my new apartment. At first, everything seemed normal, but then strange things started happening. I would wake up to find the {object} had moved during the night. Sometimes I would hear {sound} coming from that room, even when no one was there. My friends thought I was imagining things until they stayed over one night. We all witnessed the {phenomenon} together - the {object} began to {action} on its own. Later, I discovered that my grandmother had tried to warn me about this {object} before she died. She said it was cursed by {curse_origin} and should never be kept in a home. But by then, it was too late to get rid of it.",
        "variables": {
            "object": ["antique mirror", "music box", "rocking chair", "painting", "jewelry box", "grandfather clock"],
            "room": ["bedroom", "living room", "study", "hallway", "basement", "attic"],
            "sound": ["soft music", "ticking", "creaking", "whispers", "scratching", "humming"],
            "phenomenon": ["impossible sight", "terrifying event", "supernatural occurrence", "ghostly manifestation"],
            "action": ["rock back and forth", "play music", "glow with an eerie light", "move across the floor", "emit strange sounds"],
            "curse_origin": ["its previous owner", "a tragic accident", "an ancient ritual", "a vengeful spirit", "dark magic"]
        }
    },
    {
        "title": "The {time_period} Encounter",
        "content": "It was during {season} when I had my first paranormal experience. I was {activity} in the {location} when I noticed something wasn't right. The air grew {temperature} and I could sense a presence watching me. Suddenly, I heard {sound} that seemed to come from everywhere and nowhere at once. When I turned around, I saw {apparition} standing just {distance} away from me. The figure was {description} and seemed to be trying to communicate something important. I tried to speak, but no words came out. The encounter lasted only {duration}, but it felt like an eternity. As quickly as it appeared, the presence vanished, leaving behind only {evidence}. I later learned that {backstory}, which explained everything I had witnessed that {time_period}.",
        "variables": {
            "time_period": ["night", "evening", "afternoon", "early morning", "late night", "dawn"],
            "season": ["a cold winter night", "autumn", "spring", "a stormy evening", "summer"],
            "activity": ["reading", "cooking", "working", "cleaning", "sleeping", "watching TV"],
            "location": ["living room", "kitchen", "bedroom", "study", "basement", "garden"],
            "temperature": ["cold", "freezing", "unnaturally chilly", "ice-cold"],
            "sound": ["footsteps", "whispers", "a child's laughter", "sobbing", "chains rattling"],
            "apparition": ["a woman in white", "a shadowy figure", "an elderly man", "a young child", "a soldier"],
            "distance": ["a few feet", "across the room", "by the window", "in the doorway", "near the stairs"],
            "description": ["translucent", "pale and sorrowful", "wearing old-fashioned clothes", "missing facial features"],
            "duration": ["a few seconds", "several minutes", "what felt like hours", "an instant"],
            "evidence": ["a cold spot", "the scent of old roses", "a mysterious stain", "moved furniture"],
            "backstory": ["a tragedy had occurred here years ago", "someone had died in this very spot", "this was a former burial ground"]
        }
    }
]

SOURCES = ["reddit_ghoststories", "ptt_marvel"]
AUTHORS = [
    "GhostHunter2023", "NightOwl99", "SupernaturalSeeker", "ParanormalJoe", "SpiritWhisperer",
    "HauntedHomeowner", "GhostlyGamer", "SpookyStoryTeller", "EerieExplorer", "PhantomFinder",
    "PoltergeistPursuit", "SpectralSeeker", "GrimReaper92", "ShadowHunter", "MysticMind",
    "SpookyCinema", "HorrorHobbyist", "GhostGuru", "ParanormalPro", "SpiritSeer",
    "marvel_lover123", "ghost_stories_fan", "supernatural_taiwan", "horror_enthusiast",
    "paranormal_investigator", "mystery_seeker", "spooky_tales", "urban_legend_hunter"
]

def generate_story_content(template):
    """Generate a story from a template by replacing variables"""
    title = template["title"]
    content = template["content"]
    
    # Replace variables in both title and content
    for var_name, options in template["variables"].items():
        placeholder = f"{{{var_name}}}"
        chosen_value = random.choice(options)
        title = title.replace(placeholder, chosen_value)
        content = content.replace(placeholder, chosen_value)
    
    return title, content

async def populate_bronze_data(target_count=100):
    """Populate bronze_stories table with test data"""
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host='localhost', 
            port=5432,
            database='hauntbro',
            user='postgres',
            password='postgres'
        )
        
        # Check current count
        current_count = await conn.fetchval("SELECT COUNT(*) FROM bronze_stories")
        print(f"Current bronze stories: {current_count}")
        
        stories_to_add = max(0, target_count - current_count)
        print(f"Adding {stories_to_add} new stories...")
        
        # Generate and insert stories
        for i in range(stories_to_add):
            template = random.choice(STORY_TEMPLATES)
            title, content = generate_story_content(template)
            
            source = random.choice(SOURCES)
            author = random.choice(AUTHORS)
            
            # Random post date within last year
            days_ago = random.randint(1, 365)
            post_date = datetime.now() - timedelta(days=days_ago)
            
            # Generate source URL
            if source == "reddit_ghoststories":
                source_url = f"https://reddit.com/r/ghoststories/comments/{random.randint(100000, 999999)}/{title.lower().replace(' ', '_')}"
            else:
                source_url = f"https://ptt.cc/bbs/marvel/{random.randint(10000, 99999)}.html"
            
            # Add some variety to content length
            if random.random() < 0.3:  # 30% chance of longer stories
                additional_content = " " + random.choice([
                    "The experience changed my perspective on the supernatural forever. I now know that there are things in this world that cannot be explained by science or logic.",
                    "I've since moved away from that place, but the memories of that encounter still haunt me to this day. Sometimes I wonder if the spirit followed me.",
                    "After researching the history of the location, I discovered that my experience was not unique. Many others had reported similar encounters over the years.",
                    "I decided to consult with a paranormal investigator who confirmed that the area had significant spiritual activity. The investigation revealed even more disturbing details.",
                    "To this day, I cannot explain what I witnessed. The rational part of my mind wants to dismiss it, but I know what I saw was real."
                ])
                content += additional_content
            
            await conn.execute("""
                INSERT INTO bronze_stories (title, content, source, source_url, author, post_date, raw_metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, title, content, source, source_url, author, post_date, 
            f'{{"generated": true, "template_used": {STORY_TEMPLATES.index(template)}, "word_count": {len(content.split())}}}')
            
            if (i + 1) % 10 == 0:
                print(f"Added {i + 1} stories...")
        
        # Final count
        final_count = await conn.fetchval("SELECT COUNT(*) FROM bronze_stories")
        print(f"✅ Total bronze stories: {final_count}")
        
        # Show stats
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total,
                AVG(LENGTH(content)) as avg_length,
                MIN(LENGTH(content)) as min_length,
                MAX(LENGTH(content)) as max_length,
                AVG(ARRAY_LENGTH(STRING_TO_ARRAY(content, ' '), 1)) as avg_words
            FROM bronze_stories
        """)
        
        print(f"📊 Bronze Layer Statistics:")
        print(f"   Total stories: {stats['total']}")
        print(f"   Avg content length: {int(stats['avg_length'])} characters")
        print(f"   Length range: {stats['min_length']} - {stats['max_length']} characters")
        print(f"   Avg word count: {int(stats['avg_words'])} words")
        
        await conn.close()
        return final_count
        
    except Exception as e:
        print(f"❌ Error populating bronze data: {e}")
        return 0

if __name__ == "__main__":
    asyncio.run(populate_bronze_data(100))