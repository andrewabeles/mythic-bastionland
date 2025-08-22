import streamlit as st
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import copy
from PIL import Image
import io

@dataclass
class Character:
    """Represents a Mythic Bastionland character with combat stats."""
    name: str
    vigor: int
    max_vigor: int
    clarity: int
    max_clarity: int
    spirit: int
    max_spirit: int
    guard: int
    max_guard: int
    armor: int
    is_mortally_wounded: bool = False
    is_wounded: bool = False
    is_impaired: bool = False
    is_fatigued: bool = False
    is_scarred: bool = False
    is_alive: bool = True
    notes: str = ""
    profile_image: bytes = None
    
    def apply_damage(self, damage: int) -> Dict[str, any]:
        """Apply damage following Mythic Bastionland rules."""
        original_damage = damage
        damage_log = []
        
        # Step 1: Subtract Armor
        if self.armor > 0:
            armor_absorbed = min(damage, self.armor)
            damage -= armor_absorbed
            damage_log.append(f"Armor absorbed {armor_absorbed} damage")
        
        # Step 2: Subtract from Guard
        scar_inflicted = False
        if damage > 0 and self.guard > 0:
            original_guard = self.guard
            guard_damage = min(damage, self.guard)
            self.guard -= guard_damage
            damage -= guard_damage
            damage_log.append(f"Guard reduced by {guard_damage} (now {self.guard})")
            
            # Check for Scar (Guard reduced to exactly 0)
            if original_guard > 0 and self.guard == 0:
                self.is_scarred = True
                scar_inflicted = True
                damage_log.append("🔥 SCAR inflicted! (Guard reduced to 0)")
        
        # Step 3: Subtract remaining damage from Vigor
        vigor_damage = 0
        mortal_wound_inflicted = False
        wounded = False
        
        if damage > 0:
            original_vigor = self.vigor
            vigor_damage = min(damage, self.vigor)
            self.vigor -= vigor_damage
            damage_log.append(f"Vigor reduced by {vigor_damage} (now {self.vigor})")
            
            # Character becomes wounded when losing any Vigor
            if vigor_damage > 0:
                self.is_wounded = True
                wounded = True
                damage_log.append("🩸 Character is now WOUNDED!")
            
            # Check for Mortal Wound (half or more of current Vigor)
            if vigor_damage >= (original_vigor / 2):
                self.is_mortally_wounded = True
                mortal_wound_inflicted = True
                damage_log.append("⚠️ MORTAL WOUND inflicted!")
            
            # Check for death
            if self.vigor <= 0:
                self.is_alive = False
                damage_log.append("💀 CHARACTER SLAIN!")
        
        return {
            "original_damage": original_damage,
            "final_damage": original_damage - damage,
            "damage_log": damage_log,
            "wounded": wounded,
            "mortal_wound_inflicted": mortal_wound_inflicted,
            "scar_inflicted": scar_inflicted,
            "character_slain": not self.is_alive
        }
    
    def heal_vigor(self, amount: int):
        """Heal Vigor up to maximum."""
        self.vigor = min(self.vigor + amount, self.max_vigor)
        # If fully healed, remove wounded and mortally wounded status
        if self.vigor == self.max_vigor:
            self.is_wounded = False
            self.is_mortally_wounded = False
    
    def restore_guard(self, amount: int):
        """Restore Guard up to maximum."""
        self.guard = min(self.guard + amount, self.max_guard)
    
    def reset_to_full(self):
        """Reset all stats to maximum values."""
        self.vigor = self.max_vigor
        self.clarity = self.max_clarity
        self.spirit = self.max_spirit
        self.guard = self.max_guard
        self.is_mortally_wounded = False
        self.is_wounded = False
        self.is_impaired = False
        self.is_fatigued = False
        self.is_scarred = False
        self.is_alive = True

def load_characters() -> Dict[str, Character]:
    """Load characters from session state."""
    if 'characters' not in st.session_state:
        st.session_state.characters = {}
    return st.session_state.characters

def save_character(character: Character):
    """Save a character to session state."""
    if 'characters' not in st.session_state:
        st.session_state.characters = {}
    st.session_state.characters[character.name] = character

def delete_character(name: str):
    """Delete a character from session state."""
    if 'characters' in st.session_state and name in st.session_state.characters:
        del st.session_state.characters[name]


def character_creation_page(characters):
    """Character creation page."""
    st.header("Create New Character")
    
    with st.form("character_creation"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Character Name", placeholder="Enter character name")
            vigor = st.number_input("Vigor", min_value=1, max_value=50, value=10)
            clarity = st.number_input("Clarity", min_value=1, max_value=50, value=10)
            spirit = st.number_input("Spirit", min_value=1, max_value=50, value=10)
        
        with col2:
            guard = st.number_input("Guard", min_value=0, max_value=50, value=5)
            armor = st.number_input("Armor", min_value=0, max_value=20, value=1)
        
        # Notes field spanning both columns
        notes = st.text_area(
            "Notes (Optional)", 
            placeholder="Add any notes about this character (equipment, backstory, special abilities, etc.)",
            height=80
        )
        
        # Profile image upload
        uploaded_image = st.file_uploader(
            "Profile Image (Optional)",
            type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
            help="Upload a character portrait or photo to help identify them at the table"
        )
        
        submitted = st.form_submit_button("Create Character")
        
        if submitted:
            if name and name not in characters:
                # Process uploaded image
                image_data = None
                if uploaded_image is not None:
                    image_data = uploaded_image.read()
                
                new_character = Character(
                    name=name,
                    vigor=vigor,
                    max_vigor=vigor,
                    clarity=clarity,
                    max_clarity=clarity,
                    spirit=spirit,
                    max_spirit=spirit,
                    guard=guard,
                    max_guard=guard,
                    armor=armor,
                    notes=notes,
                    profile_image=image_data
                )
                save_character(new_character)
                st.success(f"Character '{name}' created successfully!")
                st.rerun()
            elif name in characters:
                st.error("A character with this name already exists!")
            else:
                st.error("Please enter a character name!")

def character_management_page(characters):
    """Character management page."""
    st.header("Character Management")
    
    if not characters:
        st.info("No characters created yet. Go to 'Character Creation' to add some!")
        return
    
    # Character selection
    selected_char_name = st.selectbox("Select Character:", list(characters.keys()))
    
    if selected_char_name:
        character = characters[selected_char_name]
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader(f"📋 {character.name}")
            
            # Status indicators
            if not character.is_alive:
                st.error("💀 SLAIN")
            elif character.is_mortally_wounded:
                st.warning("⚠️ MORTALLY WOUNDED")
            elif character.is_wounded:
                st.warning("🩸 WOUNDED")
            else:
                st.success("✅ Healthy")
            
            # Additional status indicators
            status_cols = st.columns(3)
            with status_cols[0]:
                if character.is_impaired:
                    st.warning("🔴 IMPAIRED")
            with status_cols[1]:
                if character.is_fatigued:
                    st.warning("😴 FATIGUED")
            with status_cols[2]:
                if character.is_scarred:
                    st.warning("🔥 SCARRED")
            
            # Stats display
            st.markdown("### Current Stats")
            stats_col1, stats_col2 = st.columns(2)
            
            with stats_col1:
                st.metric("Vigor", f"{character.vigor}/{character.max_vigor}")
                st.metric("Clarity", f"{character.clarity}/{character.max_clarity}")
                st.metric("Spirit", f"{character.spirit}/{character.max_spirit}")
            
            with stats_col2:
                st.metric("Guard", f"{character.guard}/{character.max_guard}")
                st.metric("Armor", character.armor)
        
        with col2:
            st.subheader("Quick Actions")
            
            # Healing/Restoration
            if st.button("🏥 Full Heal", key=f"heal_{selected_char_name}"):
                character.reset_to_full()
                save_character(character)
                st.success("Character fully healed!")
                st.rerun()
            
            # Manual stat adjustments
            st.markdown("**Manual Adjustments:**")
            
            vigor_change = st.number_input("Vigor +/-", value=0, key=f"vigor_{selected_char_name}")
            if st.button("Apply Vigor Change", key=f"apply_vigor_{selected_char_name}"):
                character.vigor = max(0, min(character.vigor + vigor_change, character.max_vigor))
                if character.vigor <= 0:
                    character.is_alive = False
                elif character.vigor == character.max_vigor:
                    character.is_wounded = False
                    character.is_mortally_wounded = False
                save_character(character)
                st.rerun()
            
            guard_change = st.number_input("Guard +/-", value=0, key=f"guard_{selected_char_name}")
            if st.button("Apply Guard Change", key=f"apply_guard_{selected_char_name}"):
                character.guard = max(0, min(character.guard + guard_change, character.max_guard))
                save_character(character)
                st.rerun()
            
            # Status toggles
            st.markdown("**Status Toggles:**")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button(
                    f"{'✅ Clear Impaired' if character.is_impaired else '🔴 Mark Impaired'}", 
                    key=f"toggle_impaired_{selected_char_name}",
                    type="secondary"
                ):
                    character.is_impaired = not character.is_impaired
                    save_character(character)
                    st.rerun()
            
            with col_b:
                if st.button(
                    f"{'✅ Clear Fatigued' if character.is_fatigued else '😴 Mark Fatigued'}", 
                    key=f"toggle_fatigued_{selected_char_name}",
                    type="secondary"
                ):
                    character.is_fatigued = not character.is_fatigued
                    save_character(character)
                    st.rerun()
            
            with col_c:
                if st.button(
                    f"{'✅ Clear Scar' if character.is_scarred else '🔥 Mark Scarred'}", 
                    key=f"toggle_scarred_{selected_char_name}",
                    type="secondary"
                ):
                    character.is_scarred = not character.is_scarred
                    save_character(character)
                    st.rerun()
        
        with col3:
            st.subheader("Character Actions")
            
            # Profile Image section
            with st.expander("🖼️ Profile Image", expanded=bool(character.profile_image)):
                if character.profile_image:
                    st.markdown("**Current Profile Image:**")
                    try:
                        image = Image.open(io.BytesIO(character.profile_image))
                        st.image(image, width=200, caption=f"{character.name}'s Profile")
                    except Exception as e:
                        st.error("Error displaying image. Please upload a new one.")
                
                st.markdown("**Upload or change profile image:**")
                new_image = st.file_uploader(
                    "Choose image file",
                    type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
                    key=f"image_upload_{selected_char_name}",
                    help="Upload a character portrait or photo"
                )
                
                col_save_img, col_clear_img = st.columns(2)
                with col_save_img:
                    if st.button("💾 Save Image", key=f"save_image_{selected_char_name}"):
                        if new_image is not None:
                            character.profile_image = new_image.read()
                            save_character(character)
                            st.success("Image saved!")
                            st.rerun()
                        else:
                            st.warning("Please select an image first!")
                
                with col_clear_img:
                    if st.button("🗑️ Remove Image", key=f"clear_image_{selected_char_name}"):
                        character.profile_image = None
                        save_character(character)
                        st.success("Image removed!")
                        st.rerun()
            
            # Notes section
            with st.expander("📝 Character Notes", expanded=bool(character.notes)):
                st.markdown("**Add or edit notes about this character:**")
                notes_text = st.text_area(
                    "Notes",
                    value=character.notes,
                    height=100,
                    placeholder="Add notes about this character (equipment, backstory, special abilities, etc.)",
                    key=f"notes_{selected_char_name}",
                    label_visibility="collapsed"
                )
                
                col_save, col_clear = st.columns(2)
                with col_save:
                    if st.button("💾 Save Notes", key=f"save_notes_{selected_char_name}"):
                        character.notes = notes_text
                        save_character(character)
                        st.success("Notes saved!")
                        st.rerun()
                
                with col_clear:
                    if st.button("🗑️ Clear Notes", key=f"clear_notes_{selected_char_name}"):
                        character.notes = ""
                        save_character(character)
                        st.success("Notes cleared!")
                        st.rerun()
                
                if character.notes:
                    st.markdown("**Current Notes:**")
                    st.info(character.notes)
            
            # Edit character
            with st.expander("✏️ Edit Character"):
                with st.form(f"edit_{selected_char_name}"):
                    new_max_vigor = st.number_input("Max Vigor", value=character.max_vigor, min_value=1)
                    new_max_clarity = st.number_input("Max Clarity", value=character.max_clarity, min_value=1)
                    new_max_spirit = st.number_input("Max Spirit", value=character.max_spirit, min_value=1)
                    new_max_guard = st.number_input("Max Guard", value=character.max_guard, min_value=0)
                    new_armor = st.number_input("Armor", value=character.armor, min_value=0)
                    
                    if st.form_submit_button("Update Character"):
                        character.max_vigor = new_max_vigor
                        character.max_clarity = new_max_clarity
                        character.max_spirit = new_max_spirit
                        character.max_guard = new_max_guard
                        character.armor = new_armor
                        
                        # Adjust current values if they exceed new maximums
                        character.vigor = min(character.vigor, character.max_vigor)
                        character.clarity = min(character.clarity, character.max_clarity)
                        character.spirit = min(character.spirit, character.max_spirit)
                        character.guard = min(character.guard, character.max_guard)
                        
                        save_character(character)
                        st.success("Character updated!")
                        st.rerun()
            
            # Delete character
            if st.button("🗑️ Delete Character", key=f"delete_{selected_char_name}"):
                delete_character(selected_char_name)
                st.success(f"Character '{selected_char_name}' deleted!")
                st.rerun()

def combat_resolution_page(characters):
    """Combat resolution page."""
    st.header("Combat Damage Resolution")
    
    if not characters:
        st.info("No characters created yet. Go to 'Character Creation' to add some!")
        return
    
    # Filter out dead characters for combat
    alive_characters = {name: char for name, char in characters.items() if char.is_alive}
    
    if not alive_characters:
        st.warning("No living characters available for combat!")
        return
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Apply Damage")
        
        # Initialize selected target in session state if not exists
        if 'selected_target' not in st.session_state:
            st.session_state.selected_target = list(alive_characters.keys())[0] if alive_characters else None
        
        # Ensure selected target is still alive and valid
        if st.session_state.selected_target not in alive_characters:
            st.session_state.selected_target = list(alive_characters.keys())[0] if alive_characters else None
        
        # Target selection (can be overridden by clicking characters below)
        target_name = st.selectbox(
            "Target Character:", 
            list(alive_characters.keys()),
            index=list(alive_characters.keys()).index(st.session_state.selected_target) if st.session_state.selected_target in alive_characters else 0
        )
        
        # Update session state when selectbox changes
        if target_name != st.session_state.selected_target:
            st.session_state.selected_target = target_name
        
        damage_amount = st.number_input("Damage Amount", min_value=0, value=1)
        
        # Show selected target info
        if target_name:
            selected_char = characters[target_name]
            st.info(f"🎯 **Selected Target:** {target_name} | Vigor: {selected_char.vigor}/{selected_char.max_vigor} | Guard: {selected_char.guard}/{selected_char.max_guard} | Armor: {selected_char.armor}")
        
        # Combat action buttons
        col_damage, col_impaired, col_fatigued = st.columns([2, 1, 1])
        
        with col_damage:
            if st.button("Apply Damage", type="primary", use_container_width=True):
                if target_name and damage_amount > 0:
                    target_character = characters[target_name]
                    result = target_character.apply_damage(damage_amount)
                    save_character(target_character)
                    
                    # Store result in session state for display
                    st.session_state.last_damage_result = result
                    st.session_state.last_target = target_name
                    st.rerun()
        
        with col_impaired:
            if target_name:
                target_char = characters[target_name]
                impaired_button_text = "✅ Clear Impaired" if target_char.is_impaired else "🔴 Mark Impaired"
                if st.button(impaired_button_text, key="combat_impaired", use_container_width=True):
                    target_char.is_impaired = not target_char.is_impaired
                    save_character(target_char)
                    st.rerun()
        
        with col_fatigued:
            if target_name:
                target_char = characters[target_name]
                fatigued_button_text = "✅ Clear Fatigued" if target_char.is_fatigued else "😴 Mark Fatigued"
                if st.button(fatigued_button_text, key="combat_fatigued", use_container_width=True):
                    target_char.is_fatigued = not target_char.is_fatigued
                    save_character(target_char)
                    st.rerun()
    
    with col2:
        st.subheader("Damage Resolution Log")
        
        if hasattr(st.session_state, 'last_damage_result') and hasattr(st.session_state, 'last_target'):
            result = st.session_state.last_damage_result
            target_name = st.session_state.last_target
            
            st.markdown(f"**Target:** {target_name}")
            st.markdown(f"**Incoming Damage:** {result['original_damage']}")
            
            for log_entry in result['damage_log']:
                if "MORTAL WOUND" in log_entry:
                    st.error(log_entry)
                elif "SLAIN" in log_entry:
                    st.error(log_entry)
                elif "Armor absorbed" in log_entry:
                    st.info(log_entry)
                else:
                    st.warning(log_entry)
    
    # Character Overview Section
    st.subheader("Character Overview")
    
    # View toggle
    view_mode = st.radio("View Mode:", ["Cards", "Table"], horizontal=True)
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status:",
            ["All", "Alive", "Dead", "Wounded", "Mortally Wounded", "Impaired", "Fatigued", "Scarred"]
        )
    with col2:
        sort_by = st.selectbox(
            "Sort by:",
            ["Name", "Vigor", "Guard"]
        )
    
    # Filter characters based on status
    filtered_chars = {}
    for name, char in characters.items():
        if status_filter == "All":
            filtered_chars[name] = char
        elif status_filter == "Alive" and char.is_alive:
            filtered_chars[name] = char
        elif status_filter == "Dead" and not char.is_alive:
            filtered_chars[name] = char
        elif status_filter == "Wounded" and char.is_alive and char.is_wounded:
            filtered_chars[name] = char
        elif status_filter == "Mortally Wounded" and char.is_alive and char.is_mortally_wounded:
            filtered_chars[name] = char
        elif status_filter == "Impaired" and char.is_alive and char.is_impaired:
            filtered_chars[name] = char
        elif status_filter == "Fatigued" and char.is_alive and char.is_fatigued:
            filtered_chars[name] = char
        elif status_filter == "Scarred" and char.is_alive and char.is_scarred:
            filtered_chars[name] = char
    
    if not filtered_chars:
        st.warning(f"No characters match the filter: {status_filter}")
    else:
        # Sort characters
        if sort_by == "Name":
            sorted_chars = dict(sorted(filtered_chars.items()))
        elif sort_by == "Vigor":
            sorted_chars = dict(sorted(filtered_chars.items(), key=lambda x: x[1].vigor, reverse=True))
        elif sort_by == "Guard":
            sorted_chars = dict(sorted(filtered_chars.items(), key=lambda x: x[1].guard, reverse=True))
        
        if view_mode == "Cards":
            # Card view
            st.markdown(f"**📋 {len(sorted_chars)} Character(s)**")
            
            # Display cards in rows of 3
            chars_list = list(sorted_chars.items())
            for i in range(0, len(chars_list), 3):
                cols = st.columns(3)
                for j, (name, character) in enumerate(chars_list[i:i+3]):
                    with cols[j]:
                        # Card container
                        with st.container():
                            # Profile image
                            if character.profile_image:
                                try:
                                    image = Image.open(io.BytesIO(character.profile_image))
                                    st.image(image, width=150, caption=name)
                                except Exception:
                                    st.markdown(f"### {name}")
                                    st.caption("🖼️ Image error")
                            else:
                                st.markdown(f"### {name}")
                            
                            # Character status
                            if not character.is_alive:
                                st.error("💀 SLAIN")
                            elif character.is_mortally_wounded:
                                st.warning("⚠️ Mortally Wounded")
                            elif character.is_wounded:
                                st.warning("🩸 Wounded")
                            else:
                                st.success("✅ Healthy")
                            
                            # Stats
                            st.markdown("**Stats:**")
                            vigor_pct = (character.vigor / character.max_vigor) * 100 if character.max_vigor > 0 else 0
                            guard_pct = (character.guard / character.max_guard) * 100 if character.max_guard > 0 else 0
                            
                            st.progress(vigor_pct / 100, text=f"Vigor: {character.vigor}/{character.max_vigor}")
                            st.progress(guard_pct / 100, text=f"Guard: {character.guard}/{character.max_guard}")
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Clarity", f"{character.clarity}/{character.max_clarity}")
                                st.metric("Armor", character.armor)
                            with col_b:
                                st.metric("Spirit", f"{character.spirit}/{character.max_spirit}")
                                if character.is_mortally_wounded:
                                    st.error("⚠️ Mortally Wounded")
                            
                            # Additional status indicators
                            if character.is_impaired or character.is_fatigued or character.is_scarred:
                                status_row = st.columns(3)
                                with status_row[0]:
                                    if character.is_impaired:
                                        st.warning("🔴 Impaired")
                                with status_row[1]:
                                    if character.is_fatigued:
                                        st.warning("😴 Fatigued")
                                with status_row[2]:
                                    if character.is_scarred:
                                        st.warning("🔥 Scarred")
                            
                            # Notes indicator
                            if character.notes:
                                with st.expander("📝 Notes"):
                                    st.write(character.notes)
                            
                            # Target selection button (only for alive characters)
                            if character.is_alive:
                                button_type = "primary" if st.session_state.get('selected_target') == name else "secondary"
                                button_text = "🎯 Selected" if st.session_state.get('selected_target') == name else "Select as Target"
                                
                                if st.button(button_text, key=f"select_{name}", type=button_type, use_container_width=True):
                                    st.session_state.selected_target = name
                                    st.rerun()
                            
                            st.divider()
        
        else:
            # Table view
            st.markdown(f"**📊 Character Table ({len(sorted_chars)} characters)**")
            
            # Add header row
            header_col1, header_col2, header_col3, header_col4, header_col5, header_col6, header_col7, header_col8, header_col9, header_col10 = st.columns([1, 1, 0.7, 0.7, 0.7, 0.7, 0.5, 1, 1, 0.8])
            with header_col1:
                st.write("**Name**")
            with header_col2:
                st.write("**Status**")
            with header_col3:
                st.write("**Vigor**")
            with header_col4:
                st.write("**Guard**")
            with header_col5:
                st.write("**Clarity**")
            with header_col6:
                st.write("**Spirit**")
            with header_col7:
                st.write("**Armor**")
            with header_col8:
                st.write("**Conditions**")
            with header_col9:
                st.write("**Notes**")
            with header_col10:
                st.write("**Target**")
            
            st.markdown("---")
            
            # Display table with selection buttons
            for name, character in sorted_chars.items():
                if not character.is_alive:
                    status = "💀 Slain"
                elif character.is_mortally_wounded:
                    status = "⚠️ Mortally Wounded"
                elif character.is_wounded:
                    status = "🩸 Wounded"
                else:
                    status = "✅ Healthy"
                
                # Create a row for each character
                col1, col2, col3, col4, col5, col6, col7, col8, col9, col10 = st.columns([1, 1, 0.7, 0.7, 0.7, 0.7, 0.5, 1, 1, 0.8])
                
                with col1:
                    if character.profile_image:
                        st.write(f"🖼️ **{name}**")
                    else:
                        st.write(f"**{name}**")
                with col2:
                    st.write(status)
                with col3:
                    st.write(f"{character.vigor}/{character.max_vigor}")
                with col4:
                    st.write(f"{character.guard}/{character.max_guard}")
                with col5:
                    st.write(f"{character.clarity}/{character.max_clarity}")
                with col6:
                    st.write(f"{character.spirit}/{character.max_spirit}")
                with col7:
                    st.write(str(character.armor))
                with col8:
                    # Show conditions
                    conditions = []
                    if character.is_impaired:
                        conditions.append("🔴 Impaired")
                    if character.is_fatigued:
                        conditions.append("😴 Fatigued")
                    if character.is_scarred:
                        conditions.append("🔥 Scarred")
                    
                    if conditions:
                        st.write(" | ".join(conditions))
                    else:
                        st.write("—")
                with col9:
                    # Show notes preview
                    if character.notes:
                        # Show first 30 characters with ellipsis
                        notes_preview = character.notes[:30] + "..." if len(character.notes) > 30 else character.notes
                        if st.button(f"📝 {notes_preview}", key=f"notes_preview_{name}", help=character.notes):
                            # This button just shows the full notes in the tooltip
                            pass
                    else:
                        st.write("—")
                with col10:
                    if character.is_alive:
                        button_type = "primary" if st.session_state.get('selected_target') == name else "secondary"
                        button_text = "🎯 Selected" if st.session_state.get('selected_target') == name else "Select"
                        
                        if st.button(button_text, key=f"table_select_{name}", type=button_type):
                            st.session_state.selected_target = name
                            st.rerun()
                    else:
                        st.write("—")
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        
        alive_count = sum(1 for char in sorted_chars.values() if char.is_alive)
        dead_count = len(sorted_chars) - alive_count
        wounded_count = sum(1 for char in sorted_chars.values() if char.is_alive and char.is_wounded)
        mortally_wounded_count = sum(1 for char in sorted_chars.values() if char.is_alive and char.is_mortally_wounded)
        impaired_count = sum(1 for char in sorted_chars.values() if char.is_alive and char.is_impaired)
        fatigued_count = sum(1 for char in sorted_chars.values() if char.is_alive and char.is_fatigued)
        scarred_count = sum(1 for char in sorted_chars.values() if char.is_alive and char.is_scarred)
        
        stat_col1, stat_col2, stat_col3, stat_col4, stat_col5, stat_col6, stat_col7 = st.columns(7)
        
        with stat_col1:
            st.metric("Total Characters", len(sorted_chars))
        with stat_col2:
            st.metric("Alive", alive_count, delta=None)
        with stat_col3:
            st.metric("Wounded", wounded_count, delta=None)
        with stat_col4:
            st.metric("Mortally Wounded", mortally_wounded_count, delta=None)
        with stat_col5:
            st.metric("Impaired", impaired_count, delta=None)
        with stat_col6:
            st.metric("Fatigued", fatigued_count, delta=None)
        with stat_col7:
            st.metric("Scarred", scarred_count, delta=None)
        
        if dead_count > 0:
            st.error(f"💀 {dead_count} character(s) have been slain")

def main():
    st.set_page_config(
        page_title="Mythic Bastionland Combat Tracker",
        page_icon="⚔️",
        layout="wide"
    )
    
    st.title("⚔️ Mythic Bastionland Combat Tracker")
    st.markdown("Track character stats and resolve combat damage automatically")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["Combat Resolution", "Character Management", "Character Creation"]
    )
    
    characters = load_characters()
    
    if page == "Character Creation":
        character_creation_page(characters)
    elif page == "Character Management":
        character_management_page(characters)
    elif page == "Combat Resolution":
        combat_resolution_page(characters)

if __name__ == "__main__":
    main()