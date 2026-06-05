# memory_extractor.py
import re
import json
import sqlite3
from typing import Dict, List, Any

# Core predefined concepts based on Feynman's background
CORE_CONCEPTS = {
    "Quantum Mechanics": r"\b(quantum|schrodinger|wavefunction|superposition|entanglement|subatomic)\b",
    "Wave-Particle Duality": r"\b(duality|wave-particle|photon|photons|light wave|interference|double[- ]slit)\b",
    "Manhattan Project": r"\b(manhattan project|los alamos|oppenheimer|atomic bomb|fission|plutonium|uranium)\b",
    "Safes & Locks": r"\b(safe|safes|lock|locks|combination|cracking|safecracking|tumbler)\b",
    "Nanotechnology": r"\b(nanotechnology|nano|room at the bottom|miniaturization|atomic scale|manipulating atoms)\b",
    "Beauty of Nature": r"\b(sunset|sunsets|beauty|awe|nature|flower|flowers|rainbow)\b",
    "Calculus & Math": r"\b(calculus|derivatives|integrals|mathematics|equations|algebra)\b",
    "Path Integrals": r"\b(path integral|path integrals|sum over histories|action principle|lagrangian)\b",
    "QED": r"\b(qed|quantum electrodynamics|feynman diagram|feynman diagrams|electron|positron)\b",
    "Computers & AI": r"\b(computer|computers|parallel computing|cellular automata|neural network|ai|artificial intelligence)\b",
    "Entropy & Physics": r"\b(entropy|thermodynamics|second law|heat|temperature|statistical mechanics)\b",
}

# Regex to discover capitalized phrases (e.g. proper nouns like "Richard Feynman", "Manhattan Project")
CAP_PHRASE_RE = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')

# Exclusions list for capitalization parser (to avoid sentence starters)
EXCLUDED_STARTERS = {"I", "The", "He", "She", "It", "We", "They", "But", "And", "A", "An", "You", "If", "Or", "As"}

class MemoryExtractor:
    @staticmethod
    def extract_session_memory(session_id: str, db_path: str = "feynman_memory.db") -> Dict[str, Any]:
        """Reads dialogue history from SQLite and parses it into a semantic concept map."""
        
        messages = []
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_store'")
            if cursor.fetchone():
                cursor.execute(
                    "SELECT message FROM message_store WHERE session_id = ? ORDER BY id ASC",
                    (session_id,)
                )
                rows = cursor.fetchall()
                for r in rows:
                    try:
                        msg_data = json.loads(r[0])
                        msg_type = msg_data.get("type", "")
                        content = msg_data.get("data", {}).get("content", "")
                        if content:
                            messages.append({"type": msg_type, "content": content})
                    except Exception:
                        continue
            conn.close()
        except Exception as e:
            print(f"[MemoryExtractor] Error querying sqlite db: {e}")

        # If no messages exist, return default starting concepts
        if not messages:
            return MemoryExtractor.get_default_network()

        # Parse concepts, node weights, and connections
        concept_mentions: Dict[str, int] = {}
        concept_snippets: Dict[str, List[Dict[str, str]]] = {}
        milestones: List[Dict[str, Any]] = []
        
        # Link connections tracker (matrix or adjacency count)
        co_occurrences: Dict[str, Dict[str, int]] = {}

        def record_mention(concept: str, snippet: str, sender: str, index: int):
            concept_mentions[concept] = concept_mentions.get(concept, 0) + 1
            if concept not in concept_snippets:
                concept_snippets[concept] = []
            concept_snippets[concept].append({
                "sender": sender,
                "text": snippet
            })
            
            # Record milestone when a concept is first introduced
            if concept_mentions[concept] == 1:
                milestones.append({
                    "timestamp": f"Exchange #{index}",
                    "concept": concept,
                    "text": snippet[:100] + ("..." if len(snippet) > 100 else "")
                })

        # Slide over messages in turns (human prompt + AI response = 1 turn)
        turn_index = 1
        for i in range(0, len(messages), 2):
            human_msg = messages[i]
            ai_msg = messages[i+1] if i + 1 < len(messages) else None
            
            turn_text = human_msg["content"]
            if ai_msg:
                turn_text += " " + ai_msg["content"]
            
            detected_in_turn = set()
            
            # 1. Predefined concepts matching
            for concept_name, pattern in CORE_CONCEPTS.items():
                if re.search(pattern, turn_text, re.IGNORECASE):
                    detected_in_turn.add(concept_name)
                    record_mention(
                        concept_name, 
                        ai_msg["content"] if ai_msg else human_msg["content"], 
                        "feynman" if ai_msg else "human",
                        turn_index
                    )

            # 2. Dynamic proper noun matching (sequences of capitalized words)
            phrases = CAP_PHRASE_RE.findall(turn_text)
            for phrase in phrases:
                words = phrase.split()
                # Exclude common sentence starters if phrase is a single word (handled by regex requiring 2+ words anyway)
                if words[0] in EXCLUDED_STARTERS or len(phrase) > 30:
                    continue
                # Normalize and register dynamic concept
                dynamic_concept = phrase.title().strip()
                detected_in_turn.add(dynamic_concept)
                record_mention(
                    dynamic_concept, 
                    ai_msg["content"] if ai_msg else human_msg["content"], 
                    "feynman" if ai_msg else "human",
                    turn_index
                )

            # 3. Establish co-occurrence links between all concepts in this turn
            detected_list = list(detected_in_turn)
            for j in range(len(detected_list)):
                c1 = detected_list[j]
                if c1 not in co_occurrences:
                    co_occurrences[c1] = {}
                for k in range(j + 1, len(detected_list)):
                    c2 = detected_list[k]
                    co_occurrences[c1][c2] = co_occurrences[c1].get(c2, 0) + 1

            turn_index += 1

        # Format node structures
        nodes = []
        for concept, weight in concept_mentions.items():
            category = "predefined" if concept in CORE_CONCEPTS else "dynamic"
            # Limit snippet counts
            snippets = concept_snippets.get(concept, [])[:5]
            nodes.append({
                "id": concept,
                "label": concept,
                "weight": weight,
                "category": category,
                "snippets": snippets
            })

        # Format link structures
        links = []
        for source, targets in co_occurrences.items():
            for target, val in targets.items():
                links.append({
                    "source": source,
                    "target": target,
                    "value": val
                })

        # Sort milestones by exchange index
        milestones = sorted(milestones, key=lambda m: int(m["timestamp"].split("#")[1]))

        # Edge case: if concepts were mentioned but no links were formed, connect all to a central "Richard Feynman" hub
        if nodes and not links:
            nodes.append({
                "id": "Richard Feynman",
                "label": "Richard Feynman",
                "weight": 2,
                "category": "persona",
                "snippets": [{"sender": "ai", "text": "Let's figure it out together!"}]
            })
            for node in nodes:
                if node["id"] != "Richard Feynman":
                    links.append({
                        "source": "Richard Feynman",
                        "target": node["id"],
                        "value": 1
                    })

        return {
            "nodes": nodes,
            "links": links,
            "milestones": milestones
        }

    @staticmethod
    def get_default_network() -> Dict[str, Any]:
        """Returns a baseline visual conceptual network for empty dialogue channels."""
        return {
            "nodes": [
                {"id": "Richard Feynman", "label": "Richard Feynman", "weight": 3, "category": "persona", "snippets": [{"sender": "ai", "text": "I'm Richard Feynman. Let's figure out how nature works!"}]},
                {"id": "Quantum Mechanics", "label": "Quantum Mechanics", "weight": 1, "category": "predefined", "snippets": [{"sender": "ai", "text": "Nature is quantum, and it's beautifully bizarre."}]},
                {"id": "Beauty of Nature", "label": "Beauty of Nature", "weight": 1, "category": "predefined", "snippets": [{"sender": "ai", "text": "The sunset is a gorgeous optical trick."}]},
                {"id": "Safes & Locks", "label": "Safes & Locks", "weight": 1, "category": "predefined", "snippets": [{"sender": "ai", "text": "Cracking safes in Los Alamos was just a fun puzzle!"}]},
                {"id": "Wave-Particle Duality", "label": "Wave-Particle Duality", "weight": 1, "category": "predefined", "snippets": [{"sender": "ai", "text": "Is it a wave or a particle? It's both!"}]}
            ],
            "links": [
                {"source": "Richard Feynman", "target": "Quantum Mechanics", "value": 1},
                {"source": "Richard Feynman", "target": "Beauty of Nature", "value": 1},
                {"source": "Richard Feynman", "target": "Safes & Locks", "value": 1},
                {"source": "Richard Feynman", "target": "Wave-Particle Duality", "value": 1}
            ],
            "milestones": [
                {"timestamp": "Start", "concept": "Richard Feynman", "text": "Digital twin initialized and ready. Type a prompt to begin."}
            ]
        }
