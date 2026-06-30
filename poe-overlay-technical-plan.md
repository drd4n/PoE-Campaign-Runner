# Technical Plan: Path of Exile 1 Campaign Map Helper Overlay

## Goal

Build a standalone desktop overlay (`poe-campaign-overlay/`) that watches the PoE `Client.txt` log in real-time, detects zone transitions, and displays a step-by-step objective list for the current campaign zone in a transparent, always-on-top, click-through PyQt6 window fixed at the top-right corner of the screen. The overlay hides when the player is in an unknown zone (hideout, endgame maps). Duplicate zone names across acts (e.g. "The Coast" in Acts 1 and 6) are resolved by tracking which act the player is in via milestone zones.

---



## Project layout

```
poe-campaign-overlay/
├── main.py           # entry point
├── overlay.py        # PyQt6 transparent window
├── log_watcher.py    # tails Client.txt, emits signals
├── zone_data.py      # loads zones.json, tracks act, resolves steps
├── config.py         # Client.txt discovery + config.json persistence
├── zones.json        # all campaign zone data (Acts 1–10)
├── build_zones.py    # one-off script to regenerate zones.json from raw text
└── requirements.txt
```

---



## Step 1 — `requirements.txt`

**File:** `poe-campaign-overlay/requirements.txt`

```
PyQt6>=6.6.0
```

---



## Step 2 — `zones.json` schema and data

**File:** `poe-campaign-overlay/zones.json`

Schema:

```jsonc
{
  // Zones that trigger an act change when entered.
  // Rule: only advance if milestones[zone] > current_act.
  // Act 6 is a special case handled in code (Lioneye's Watch when current_act == 5).
  "milestones": {
    "Twilight Strand": 1,
    "Southern Forest": 2,
    "City of Sarn": 3,
    "Aqueduct": 4,
    "Slave Pens": 5,
    "The Bridge Encampment": 7,
    "Sarn Ramparts": 8,
    "Blood Aqueduct": 9,
    "Oriath Docks": 10
  },

  // Zones keyed by exact name as it appears in Client.txt.
  // Each zone maps act number (string) → step list.
  // Zones that only appear in one act use a single key.
  "zones": {
    "Twilight Strand": {
      "1": { "steps": ["Kill Hillock", "Go to Town"] }
    },
    "Lioneye's Watch": {
      "1": { "steps": ["Talk to NPCs", "Go to The Coast"] },
      "6": { "steps": ["Talk to NPCs", "Go to The Coast"] }
    },
    "The Coast": {
      "1": {
        "steps": [
          "Tag Waypoint",
          "Go to Tidal Island (near WP) — once per league",
          "Kill Hailrake, get Medicine Chest (→ Quicksilver Flask from town)",
          "Go to Mud Flats"
        ]
      },
      "6": {
        "steps": [
          "Tag Waypoint",
          "Go to Tidal Island",
          "Get Bestel's Manuscript",
          "TP to Town, talk to NPCs",
          "Go to Mud Flats"
        ]
      }
    },
    "Tidal Island": {
      "1": { "steps": ["Kill Hailrake", "Get Medicine Chest", "TP to Town"] },
      "6": { "steps": ["Get Bestel's Manuscript", "TP to Town"] }
    },
    "Mud Flats": {
      "1": {
        "steps": [
          "Get Roseus Glyph, Ammonite Glyph, Haliotis Glyph from Rhoa Nests",
          "Activate Strange Glyph Wall",
          "Go to Submerged Passage"
        ]
      },
      "6": {
        "steps": [
          "Kill Dishonoured Queen",
          "Take Eye of Conquest",
          "Go to Karui Fortress (top/left)"
        ]
      }
    },
    "Submerged Passage": {
      "1": { "steps": ["Tag Waypoint", "Go to Flooded Depths", "Then go to The Ledge"] }
    },
    "Flooded Depths": {
      "1": { "steps": ["Kill Dweller of the Deep", "TP to Town"] }
    },
    "The Ledge": {
      "1": { "steps": ["Tag Waypoint", "Go to The Climb"] }
    },
    "The Climb": {
      "1": { "steps": ["Enter Lower Prison"] }
    },
    "Lower Prison": {
      "1": { "steps": ["Once per league: Complete Trial", "Go to Upper Prison"] },
      "6": { "steps": ["Tag Waypoint", "Once per league: Solve Trial", "Go to Shavronne's Tower"] }
    },
    "Upper Prison": {
      "1": { "steps": ["Enter Warden's Quarters", "Follow blood to Warden's Chambers"] }
    },
    "Warden's Chambers": {
      "1": { "steps": ["Kill Brutus", "Go to Prisoner's Gate", "Tag WP near entry", "TP to Town"] }
    },
    "Prisoner's Gate": {
      "1": { "steps": ["Go to Ship Graveyard"] },
      "6": {
        "steps": [
          "Go to Valley of the Fire Drinker (middle-right)",
          "Defeat Abberath",
          "Enter Cloven Pass → Valley of the Soul Drinker",
          "Finish off Abberath",
          "Go to Western Forest"
        ]
      }
    },
    "Ship Graveyard": {
      "1": {
        "steps": [
          "Tag Waypoint",
          "Enter Ship Graveyard Cave",
          "Pick up Allflame, kill Fairgraves",
          "TP to Town, talk to NPCs",
          "Go to Cavern of Wrath"
        ]
      }
    },
    "Ship Graveyard Cave": {
      "1": { "steps": ["Pick up Allflame", "Exit cave", "Kill Fairgraves", "TP to Town"] }
    },
    "Cavern of Wrath": {
      "1": { "steps": ["Tag Waypoint", "Go to Cavern of Anger", "Enter Merveil's Lair"] }
    },
    "Cavern of Anger": {
      "1": { "steps": ["Enter Merveil's Lair"] },
      "6": { "steps": ["Take The Black Flag from chest", "Go to Beacon"] }
    },
    "Merveil's Lair": {
      "1": { "steps": ["Kill Merveil", "Kill Merveil the Twisted", "Go to Act II"] }
    },

    "Southern Forest": {
      "2": { "steps": ["Enter The Forest Encampment (town)", "Go to Old Fields (top-right exit)"] },
      "6": { "steps": ["Tag Waypoint (end of area)", "Go to Cavern of Anger (near WP)"] }
    },
    "The Forest Encampment": {
      "2": { "steps": ["Talk to NPCs", "Go to Old Fields (top-right)"] }
    },
    "Old Fields": {
      "2": {
        "steps": [
          "Enter The Den (optional) — kill Great White Beast for Quicksilver Flask",
          "Go to Crossroads"
        ]
      }
    },
    "Crossroads": {
      "2": {
        "steps": [
          "Tag Waypoint (follow road)",
          "Go to Chamber of Sins Level 1 (up/left)",
          "Later: go to Broken Bridge (up/right)",
          "Later: go to Fellshrine Ruins (right/down)"
        ]
      },
      "7": {
        "steps": [
          "Tag Waypoint (follow road)",
          "Go to Fellshrine Ruins (down/right)",
          "Later: go to Chamber of Sins (left)"
        ]
      }
    },
    "Chamber of Sins Level 1": {
      "2": { "steps": ["Tag Waypoint (centre)", "Go to Chamber of Sins Level 2"] },
      "7": {
        "steps": [
          "Place Maligaro's Map into Map Device, activate portal",
          "Enter Maligaro's Sanctum",
          "Later: talk to Silk for Obsidian Key",
          "Go to Chamber of Sins Level 2"
        ]
      }
    },
    "Chamber of Sins Level 2": {
      "2": {
        "steps": [
          "Once per league: Solve Trial",
          "Kill Fidelitas",
          "Take Baleful Gem",
          "TP to Town"
        ]
      },
      "7": {
        "steps": [
          "Once per league: Solve Trial",
          "Open Secret Passage (top/right)",
          "Go to Den"
        ]
      }
    },
    "Broken Bridge": {
      "2": {
        "steps": [
          "Tag Waypoint (follow road)",
          "Kill or Save Kraityn",
          "Take Kraityn's Amulet",
          "TP to Town"
        ]
      },
      "7": { "steps": ["Go to Crossroads (follow road/left)"] }
    },
    "Fellshrine Ruins": {
      "2": { "steps": ["Go to Crypt Level 1"] },
      "7": { "steps": ["Go to Crypt (follow road then right)"] }
    },
    "Crypt Level 1": {
      "2": { "steps": ["Once per league: Solve Trial", "Go to Crypt Level 2"] },
      "7": {
        "steps": [
          "Tag Waypoint",
          "Once per league: Solve Trial",
          "Open Sarcophagus",
          "Go to Crypt Level 2"
        ]
      }
    },
    "Crypt Level 2": {
      "2": { "steps": ["Take Golden Hand", "TP to Town — talk to Yeena for skill point"] },
      "7": { "steps": ["Take Maligaro's Map", "TP to Town"] }
    },
    "Riverways": {
      "2": {
        "steps": [
          "Tag Waypoint (follow broken road)",
          "Go to Western Forest (down)",
          "Later: Go to Wetlands (up/left)"
        ]
      },
      "7": { "steps": ["Tag Waypoint", "Go to Wetlands (up/left)"] }
    },
    "Western Forest": {
      "2": {
        "steps": [
          "Tag Waypoint (follow road)",
          "Kill or Save Alira (left/top from WP)",
          "Kill Captain Arteri (end of road)",
          "Take Thaumetic Emblem",
          "Open Thaumetic Seal",
          "Go to Weaver's Chambers (other side from Alira)"
        ]
      },
      "6": { "steps": ["Tag Waypoint (follow road)", "Go to Riverways"] },
      "7": { "steps": ["Tag Waypoint (follow road)", "Go to Riverways"] }
    },
    "Weaver's Chambers": {
      "2": {
        "steps": [
          "Enter Weaver's Nest",
          "Kill Weaver",
          "Take Maligaro's Spike",
          "TP to Town"
        ]
      }
    },
    "Wetlands": {
      "2": {
        "steps": [
          "Kill or Save Oak (middle)",
          "Take Oak's Amulet",
          "Remove Tree Roots",
          "Go to Vaal Ruins"
        ]
      },
      "6": {
        "steps": [
          "Enter Spawning Ground",
          "Destroy 3 Ryslatha's Nests",
          "Kill Ryslatha",
          "TP to Town"
        ]
      },
      "7": {
        "steps": [
          "Collect 7 Fireflies",
          "Go to Den of Despair (centre)",
          "Kill Gruthkul",
          "TP to Town"
        ]
      }
    },
    "Vaal Ruins": {
      "2": { "steps": ["Activate Ancient Seal", "Go to Northern Forest"] }
    },
    "Northern Forest": {
      "2": {
        "steps": [
          "Tag Waypoint (top)",
          "TP to Town — talk to Eramir/bandit for The Apex",
          "WP back",
          "Go to Caverns (top)"
        ]
      },
      "7": {
        "steps": [
          "Tag Waypoint",
          "Go to Causeway (top right/left)"
        ]
      }
    },
    "Caverns": {
      "2": { "steps": ["Tag Waypoint", "Go to Ancient Pyramid — enter Pyramid Apex"] }
    },
    "Pyramid Apex": {
      "2": { "steps": ["Activate Dark Altar", "Kill Vaal Oversoul", "Go to Act III"] }
    },

    "City of Sarn": {
      "3": {
        "steps": [
          "Tag Waypoint",
          "Kill Guard Captain",
          "Talk to Clarissa",
          "Go to Town (Sarn Encampment)"
        ]
      }
    },
    "Sarn Encampment": {
      "3": { "steps": ["Talk to NPCs", "Go to Slums (top-right)"] },
      "8": { "steps": ["Talk to NPCs", "Go to Toxic Conduits (left)"] }
    },
    "Slums": {
      "3": { "steps": ["Go to Crematorium", "Later: open Sewer Grating (top) with Sewer Keys"] }
    },
    "Crematorium": {
      "3": {
        "steps": [
          "Tag Waypoint",
          "Once per league: Solve Trial",
          "Kill Piety",
          "Get Tolman's Bracelet",
          "TP to Town — get Sewer Keys from Clarissa"
        ]
      }
    },
    "Sewers": {
      "3": {
        "steps": [
          "Take Bust of Gaius Sentari",
          "Tag Waypoint",
          "Take Bust of Hector Titucius and Bust of Marceus Lioneye",
          "Go to Marketplace (top)",
          "Later: open Undying Blockage → go to Ebony Barracks"
        ]
      }
    },
    "Marketplace": {
      "3": {
        "steps": [
          "Tag Waypoint",
          "Once per league: Go to Catacombs (near WP), Solve Trial",
          "TP to Town, talk to NPCs",
          "Go to Battlefront (up/left)"
        ]
      }
    },
    "Battlefront": {
      "3": {
        "steps": [
          "Tag Waypoint",
          "Take Ribbon Spool (big chest)",
          "Go to Docks (left)",
          "Later: Go to Solaris Temple Level 1 (up)"
        ]
      }
    },
    "Docks": {
      "3": {
        "steps": [
          "Tag Waypoint (near Fairgraves)",
          "Take Thaumetic Sulphite (near WP)",
          "TP to Town"
        ]
      }
    },
    "Solaris Temple Level 1": {
      "3": { "steps": ["Tag Waypoint", "Go to Solaris Temple Level 2"] },
      "8": { "steps": ["Tag Waypoint", "Go to Solaris Temple Level 2 (up from WP)"] }
    },
    "Solaris Temple Level 2": {
      "3": {
        "steps": [
          "Tag Waypoint",
          "Talk to Dialla for Infernal Talc",
          "WP to Sewers — open Undying Blockage"
        ]
      },
      "8": {
        "steps": [
          "Kill Dawn",
          "Take Sun Orb",
          "TP to Town"
        ]
      }
    },
    "Ebony Barracks": {
      "3": {
        "steps": [
          "Tag Waypoint",
          "Kill General Gravicius (up)",
          "Go to Lunaris Temple Level 1 (up)"
        ]
      }
    },
    "Lunaris Temple Level 1": {
      "3": { "steps": ["Tag Waypoint", "Go to Lunaris Temple Level 2"] },
      "8": { "steps": ["Tag Waypoint", "Go to Lunaris Temple Level 2"] }
    },
    "Lunaris Temple Level 2": {
      "3": {
        "steps": [
          "Kill Piety",
          "Take Tower Key",
          "TP to Town, talk to NPCs"
        ]
      },
      "8": {
        "steps": [
          "Kill Dusk",
          "Take Moon Orb",
          "TP to Town"
        ]
      }
    },
    "Imperial Gardens": {
      "3": {
        "steps": [
          "Tag Waypoint",
          "Once per league: Solve Trial (top)",
          "Open Locked Door (top/right)",
          "Go to Sceptre of God"
        ]
      }
    },
    "Sceptre of God": {
      "3": {
        "steps": [
          "Tag Waypoint",
          "Go to Upper Sceptre of God"
        ]
      }
    },
    "Upper Sceptre of God": {
      "3": { "steps": ["Kill Dominus", "Kill Dominus, Ascendant", "Go to Act IV"] }
    },

    "Aqueduct": {
      "4": { "steps": ["Tag Waypoint (next to entrance)", "Go to Town (Highgate)"] }
    },
    "Highgate": {
      "4": { "steps": ["Talk to NPCs", "Go to Dried Lake (bottom-left)"] },
      "9": { "steps": ["Talk to NPCs", "Go to Descent (top-right)"] }
    },
    "Dried Lake": {
      "4": {
        "steps": [
          "Kill Voll",
          "Take Deshret's Banner",
          "TP to Town — open Deshret's Seal (near Niko)"
        ]
      }
    },
    "Mines Level 1": {
      "4": { "steps": ["Go to Mines Level 2"] }
    },
    "Mines Level 2": {
      "4": { "steps": ["Tag Deshret's Spirit", "Enter Crystal Veins"] }
    },
    "Crystal Veins": {
      "4": {
        "steps": [
          "Tag Waypoint",
          "Go to Kaom's Dream",
          "Later: Go to Daresso's Dream (talk to Dialla)",
          "Later: Go to Belly of the Beast Level 1 (talk to Dialla)"
        ]
      }
    },
    "Kaom's Dream": {
      "4": { "steps": ["Go to Kaom's Stronghold"] }
    },
    "Kaom's Stronghold": {
      "4": {
        "steps": [
          "Tag Waypoint",
          "Go to Caldera of the King",
          "Kill King Kaom",
          "Take The Eye of Fury",
          "TP to Town — WP to Crystal Veins"
        ]
      }
    },
    "Daresso's Dream": {
      "4": {
        "steps": [
          "Kill Barkhul",
          "Go to Grand Arena"
        ]
      }
    },
    "Grand Arena": {
      "4": {
        "steps": [
          "Tag Waypoint",
          "Kill Unique Trio",
          "Go to Ring of Blades",
          "Kill Daresso",
          "Take The Eye of Desire",
          "TP to Town — WP to Crystal Veins"
        ]
      }
    },
    "Belly of the Beast Level 1": {
      "4": { "steps": ["Go to Belly of the Beast Level 2"] },
      "9": { "steps": ["Enter Rotting Core"] }
    },
    "Belly of the Beast Level 2": {
      "4": {
        "steps": [
          "Enter The Bowels of the Beast",
          "Kill Piety",
          "Go to Harvest"
        ]
      }
    },
    "Harvest": {
      "4": {
        "steps": [
          "Tag Waypoint",
          "Talk to Piety",
          "Enter The Black Core",
          "Kill Shavronne (take Malachai's Entrails)",
          "Kill Maligaro (take Malachai's Heart)",
          "Kill Doedre (take Malachai's Lungs)",
          "Go to Harvest — talk to Piety — re-enter Black Core",
          "Kill Piety then Malachai"
        ]
      }
    },
    "Ascent": {
      "4": { "steps": ["Walk to summit", "Activate Lever", "Go to Act V"] }
    },

    "Slave Pens": {
      "5": {
        "steps": [
          "Tag Waypoint",
          "Kill Overseer Krow",
          "Go to Town (Overseer's Tower)"
        ]
      }
    },
    "Overseer's Tower": {
      "5": { "steps": ["Talk to NPCs", "Go to Control Blocks"] }
    },
    "Control Blocks": {
      "5": {
        "steps": [
          "Pick up Miasmeter (down/left)",
          "Kill Justicar Casticus (top/right)",
          "Take Eyes of Zeal",
          "Go to Oriath Square"
        ]
      },
      "10": {
        "steps": [
          "Tag Waypoint (left of entrance)",
          "Kill Vilenta (follow right-hand wall)",
          "TP to Town"
        ]
      }
    },
    "Oriath Square": {
      "5": {
        "steps": [
          "Tag Waypoint",
          "Open Templar Courts Entrance (top right)",
          "Enter Templar Courts"
        ]
      }
    },
    "Templar Courts": {
      "5": { "steps": ["Tag Waypoint", "Go to Chamber of Innocence"] }
    },
    "The Chamber of Innocence": {
      "5": {
        "steps": [
          "Tag Waypoint",
          "Go to Sanctum of Innocence (go leftmost, then right)"
        ]
      }
    },
    "Sanctum of Innocence": {
      "5": {
        "steps": [
          "Kill High Templar Avarius",
          "Kill Innocence",
          "Go back to Chamber of Innocence → Torched Courts"
        ]
      },
      "10": {
        "steps": [
          "Kill Avarius",
          "Take The Staff of Purity",
          "TP to Town"
        ]
      }
    },
    "Torched Courts": {
      "5": { "steps": ["Go to Ruined Square"] },
      "10": { "steps": ["Go to Desecrated Chambers"] }
    },
    "Ruined Square": {
      "5": {
        "steps": [
          "Tag Waypoint (top left)",
          "Go to Ossuary (near WP) — click Tomb, pick up Sign of Purity",
          "TP to Town, talk to NPCs",
          "Go to Reliquary (down)"
        ]
      },
      "10": {
        "steps": [
          "Tag Waypoint (right/up)",
          "Go to Torched Courts (right from WP)",
          "Once per league: Go to Ossuary (next to WP) → Bone Pits, Solve Trial",
          "Talk to Innocence (right from WP)",
          "Go to Canals"
        ]
      }
    },
    "Ossuary": {
      "5": { "steps": ["Click Tomb", "Pick up Sign of Purity", "TP to Town"] }
    },
    "Reliquary": {
      "5": {
        "steps": [
          "Tag Waypoint",
          "Collect Tukohama's Tooth, Hinekora's Hair, Valako's Jaw (corners of zone)",
          "TP to Town, talk to NPCs",
          "Go to Cathedral Rooftop"
        ]
      }
    },
    "Cathedral Rooftop": {
      "5": { "steps": ["Go to Cathedral Apex (left of town square)"] },
      "10": {
        "steps": [
          "Go to Cathedral Apex (top-left)",
          "Kill Plaguewing",
          "Go to Ravaged Square (bottom-right)"
        ]
      }
    },
    "Cathedral Apex": {
      "5": { "steps": ["Activate Cradle of Purity", "Kill Kitava", "Sail to Act VI"] }
    },

    "Karui Fortress": {
      "6": {
        "steps": [
          "Enter Tukohama's Keep",
          "Kill Tukohama (right)",
          "Go to Ridge (outside Arena, then right)"
        ]
      }
    },
    "Ridge": {
      "6": { "steps": ["Tag Waypoint", "Go to Lower Prison"] }
    },
    "Shavronne's Tower": {
      "6": {
        "steps": [
          "Go to Prison Rooftop",
          "Kill Brutus and Shavronne",
          "Go to Warden's Chambers → Prisoner's Gate"
        ]
      }
    },
    "Beacon": {
      "6": {
        "steps": [
          "Tag Waypoint",
          "Refuel and light the Beacon",
          "Talk to Weylam Roth",
          "Sail to Brine King's Reef"
        ]
      }
    },
    "Brine King's Reef": {
      "6": {
        "steps": [
          "Tag Waypoint",
          "Go to Brine King's Throne",
          "Kill Tsoagoth",
          "Sail to Act VII"
        ]
      }
    },

    "The Bridge Encampment": {
      "7": { "steps": ["Talk to NPCs", "Go to Broken Bridge"] }
    },
    "Ashen Fields": {
      "7": {
        "steps": [
          "Tag Waypoint",
          "Go to Fortress Encampment (follow road to left/down)"
        ]
      }
    },
    "Den": {
      "7": { "steps": ["Tag Waypoint", "Go to Ashen Fields (top/right)"] }
    },
    "Fortress Encampment": {
      "7": { "steps": ["Kill Greust", "Go to Northern Forest (top of arena)"] }
    },
    "Dread Thicket": {
      "7": {
        "steps": [
          "Collect 7 Fireflies",
          "Go to Den of Despair (centre)",
          "Kill Gruthkul",
          "TP to Town"
        ]
      }
    },
    "Causeway": {
      "7": {
        "steps": [
          "Tag Waypoint (end of area)",
          "Take Kishara's Star from Kishara's Lockbox",
          "TP to Town — talk to Weylam for skill point",
          "Return through portal → Go to Vaal City"
        ]
      }
    },
    "Vaal City": {
      "7": {
        "steps": [
          "Tag Waypoint (middle of zone)",
          "Talk to Yeena",
          "Go to Temple of Decay Level 1"
        ]
      }
    },
    "Temple of Decay Level 1": {
      "7": { "steps": ["Go to Temple of Decay Level 2"] }
    },
    "Temple of Decay Level 2": {
      "7": { "steps": ["Kill Arakaali", "Go to Act VIII"] }
    },
    "Maligaro's Sanctum": {
      "7": {
        "steps": [
          "Kill Maligaro",
          "Take Black Venom",
          "TP to Chamber of Sins"
        ]
      }
    },

    "Sarn Ramparts": {
      "8": { "steps": ["Go to Sarn Encampment (town)"] }
    },
    "Toxic Conduits": {
      "8": {
        "steps": [
          "Open Loose Gate (end of area)",
          "Go to Doedre's Cesspool",
          "Later: Go to Quay (up/right from WP)"
        ]
      }
    },
    "Doedre's Cesspool": {
      "8": {
        "steps": [
          "Enter Cauldron",
          "Activate Valve",
          "Kill Doedre",
          "Tag Waypoint",
          "Go to Grand Promenade (down/left from WP)"
        ]
      }
    },
    "Grand Promenade": {
      "8": { "steps": ["Go to Bath House (follow right-hand fence)"] }
    },
    "Bath House": {
      "8": {
        "steps": [
          "Tag Waypoint",
          "Once per league: Solve Trial (top or left)",
          "Go to High Gardens (top or left)"
        ]
      }
    },
    "High Gardens": {
      "8": {
        "steps": [
          "Go to Pools of Terror (right)",
          "Kill Yugul",
          "TP to Town"
        ]
      }
    },
    "Lunaris Concourse": {
      "8": {
        "steps": [
          "Tag Waypoint",
          "Go to Lunaris Temple (top)",
          "Later: Go to Harbour Bridge (down/right)"
        ]
      }
    },
    "Quay": {
      "8": {
        "steps": [
          "Take Ankh of Eternity (down)",
          "Enter Resurrection Site (down/left)",
          "Kill Tolman, talk to Clarissa",
          "Go to Grain Gate (up/right)"
        ]
      }
    },
    "Grain Gate": {
      "8": {
        "steps": [
          "Tag Waypoint",
          "Kill Gemling Legion",
          "Go to Imperial Fields"
        ]
      }
    },
    "Imperial Fields": {
      "8": {
        "steps": [
          "Tag Waypoint (follow road up)",
          "Go to Solaris Temple (follow road further up)"
        ]
      }
    },
    "Harbour Bridge": {
      "8": {
        "steps": [
          "Enter Sky Shrine (middle of bridge)",
          "Activate Statue of the Sisters",
          "Kill Lunaris and Solaris",
          "Go to Act IX"
        ]
      }
    },

    "Blood Aqueduct": {
      "9": { "steps": ["Enter Highgate (town)"] }
    },
    "Descent": {
      "9": { "steps": ["Go down Supply Hoist (twice)", "Go to Vastiri Desert"] }
    },
    "Vastiri Desert": {
      "9": {
        "steps": [
          "Tag Waypoint",
          "Open Storm-Weathered Chest, kill monsters, pick up Storm Blade",
          "TP to Town — get Bottled Storm",
          "Go to Oasis (down from WP, then right)",
          "Later: Go to Foothills (up/left)"
        ]
      }
    },
    "Oasis": {
      "9": {
        "steps": [
          "Enter Sand Pit",
          "Kill Shakari",
          "TP to Town — WP to Vastiri Desert"
        ]
      }
    },
    "Foothills": {
      "9": {
        "steps": [
          "Tag Waypoint (up)",
          "Go to Boiling Lake (up/right from WP)",
          "Later: Go to Tunnel (top/left)"
        ]
      }
    },
    "Boiling Lake": {
      "9": {
        "steps": [
          "Kill Basilisk",
          "Take Basilisk Acid",
          "TP to Town — WP to Foothills"
        ]
      }
    },
    "Tunnel": {
      "9": {
        "steps": [
          "Tag Waypoint",
          "Once per league: Solve Trial (before the WP)",
          "Go to Quarry"
        ]
      }
    },
    "Quarry": {
      "9": {
        "steps": [
          "Tag Waypoint",
          "Go to Shrine of the Winds (top right/left)",
          "Kill Garukhan and Kira",
          "Take Sekhema Feather",
          "Go to Refinery (top right/left)"
        ]
      }
    },
    "Refinery": {
      "9": {
        "steps": [
          "Kill General Adus",
          "Take Trarthan Powder",
          "TP to Town, talk to NPCs",
          "WP to Quarry — talk to Sin",
          "Go to Belly of the Beast"
        ]
      }
    },
    "Rotting Core": {
      "9": {
        "steps": [
          "Enter Black Core",
          "Talk to Sin",
          "Kill Doedre, Maligaro, Shavronne in portals",
          "Kill Depraved Trinity",
          "Sail to Act X"
        ]
      }
    },

    "Oriath Docks": {
      "10": { "steps": ["Go to Cathedral Rooftop"] }
    },
    "Ravaged Square": {
      "10": {
        "steps": [
          "Tag Waypoint (right/up)",
          "Go to Torched Courts (right from WP)",
          "Once per league: Go to Ossuary → Bone Pits, Solve Trial",
          "Talk to Innocence (right from WP)",
          "Go to Control Blocks (down)"
        ]
      }
    },
    "Desecrated Chambers": {
      "10": {
        "steps": [
          "Tag Waypoint",
          "Go to Sanctum of Innocence (leftmost, then right)"
        ]
      }
    },
    "Canals": {
      "10": { "steps": ["Follow canal", "Go to Feeding Trough"] }
    },
    "The Feeding Trough": {
      "10": { "steps": ["Go to Altar of Hunger (top)"] }
    },
    "Altar of Hunger": {
      "10": {
        "steps": [
          "Kill Kitava",
          "Go to Oriath Docks",
          "Talk to Lani for skill point",
          "WARNING: -60% all resistances after this kill"
        ]
      }
    }
  }
}
```



---



## Step 3 — `config.py`

**File:** `poe-campaign-overlay/config.py`

Discovers `Client.txt` by searching known paths, falls back to `config.json`.

```python
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"

SEARCH_PATHS = [
    Path.home() / ".steam/steam/steamapps/compatdata/238960/pfx/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    Path.home() / ".local/share/Steam/steamapps/compatdata/238960/pfx/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    Path.home() / ".wine/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    Path("C:/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt"),
    Path("C:/Program Files/Grinding Gear Games/Path of Exile/logs/Client.txt"),
]


def find_client_log() -> str | None:
    """Check config.json first, then search known paths. Returns path string or None."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            path = Path(data.get("client_log_path", ""))
            if path.exists():
                return str(path)
        except (json.JSONDecodeError, OSError):
            pass

    for path in SEARCH_PATHS:
        if path.exists():
            return str(path)

    return None


def save_client_log_path(path: str) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump({"client_log_path": path}, f, indent=2)
```

---



## Step 4 — `zone_data.py`

**File:** `poe-campaign-overlay/zone_data.py`

Loads `zones.json`, tracks the current act, resolves zone entries to step lists.

```python
import json
from pathlib import Path

ZONES_FILE = Path(__file__).parent / "zones.json"
ACT6_TRIGGER = "Lioneye's Watch"  # only advances to act 6 when current_act == 5


def _load() -> dict:
    with open(ZONES_FILE, encoding="utf-8") as f:
        return json.load(f)


class ZoneTracker:
    def __init__(self):
        data = _load()
        self._milestones: dict[str, int] = data["milestones"]
        self._zones: dict[str, dict] = data["zones"]
        self.current_act: int = 0

    def enter_zone(self, zone_name: str) -> list[str] | None:
        """Update act tracking and return steps for this zone, or None if unknown."""
        self._update_act(zone_name)
        return self._resolve_steps(zone_name)

    def _update_act(self, zone_name: str) -> None:
        # Special case: Lioneye's Watch is the Act 1 town AND the Act 6 start.
        # Only advance to Act 6 if we've already completed Act 5.
        if zone_name == ACT6_TRIGGER and self.current_act == 5:
            self.current_act = 6
            return

        new_act = self._milestones.get(zone_name)
        if new_act is not None and new_act > self.current_act:
            self.current_act = new_act

    def _resolve_steps(self, zone_name: str) -> list[str] | None:
        zone = self._zones.get(zone_name)
        if not zone:
            return None

        # Try exact act match first
        entry = zone.get(str(self.current_act))

        # Fallback: zone exists in only one act (no ambiguity)
        if entry is None and len(zone) == 1:
            entry = next(iter(zone.values()))

        if entry is None:
            return None

        return entry.get("steps", [])
```

---



## Step 5 — `log_watcher.py`

**File:** `poe-campaign-overlay/log_watcher.py`

Runs on a `QThread`, tails `Client.txt` from the end (no history replay), emits `zone_changed` when a new zone is entered.

```python
import re
from PyQt6.QtCore import QThread, pyqtSignal

_ZONE_RE = re.compile(r"You have entered (.+)\.")


class LogWatcher(QThread):
    zone_changed = pyqtSignal(str)

    def __init__(self, log_path: str):
        super().__init__()
        self._log_path = log_path
        self._running = True

    def run(self) -> None:
        with open(self._log_path, encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)  # start at end — ignore history
            while self._running:
                line = f.readline()
                if line:
                    m = _ZONE_RE.search(line)
                    if m:
                        self.zone_changed.emit(m.group(1))
                else:
                    self.msleep(2000)  # poll every 2s — low CPU, zone transitions are slow anyway

    def stop(self) -> None:
        self._running = False
        self.wait()
```

---



## Step 6 — `overlay.py`

**File:** `poe-campaign-overlay/overlay.py`

Transparent, frameless, always-on-top, click-through window. Renders zone name + step list with a rounded dark background painted in `paintEvent`.

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QFont, QPainter, QColor, QPainterPath

_WIDTH = 340
_MARGIN = 16
_PADDING = 12
_BG = QColor(10, 10, 10, 210)
_ZONE_COLOR = "#e8c97a"
_STEP_COLOR = "#cccccc"


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._build_window()
        self._build_ui()

    def _build_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool               # hides from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
        self.setFixedWidth(_WIDTH)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_PADDING, _PADDING, _PADDING, _PADDING)
        layout.setSpacing(6)

        self._zone_label = QLabel()
        self._zone_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self._zone_label.setStyleSheet(f"color: {_ZONE_COLOR}; background: transparent;")
        self._zone_label.setWordWrap(True)
        layout.addWidget(self._zone_label)

        self._steps_label = QLabel()
        self._steps_label.setFont(QFont("Consolas", 10))
        self._steps_label.setStyleSheet(f"color: {_STEP_COLOR}; background: transparent;")
        self._steps_label.setWordWrap(True)
        self._steps_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._steps_label)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8, 8)
        painter.fillPath(path, _BG)

    def show_zone(self, zone_name: str, steps: list[str]) -> None:
        self._zone_label.setText(f"◆  {zone_name}")
        self._steps_label.setText("\n".join(f"  • {s}" for s in steps))
        self.adjustSize()
        self._snap_top_right()
        self.show()

    def hide_zone(self) -> None:
        self.hide()

    def _snap_top_right(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - _MARGIN, screen.top() + _MARGIN)
```

---

