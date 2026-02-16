// ============ Map Layout — The Kalevala Expanse (ESI-verified) ============
// All 10 TKE constellations + neighbor region systems matching Dotlan layout
// Gate connections verified from ESI /universe/stargates/ endpoint

const MAP_LAYOUT = {
    // ===== LAWN 6-CBBM (center-top) — EMPHASIZED =====
    "UDVW-O": { x: 480, y: 58, constellation: "6-CBBM", lawn: true },
    "UJXC-B": { x: 570, y: 48, constellation: "6-CBBM", lawn: true },
    "F48K-D": { x: 650, y: 52, constellation: "6-CBBM", lawn: true },
    "1-KCSA": { x: 575, y: 90, constellation: "6-CBBM", lawn: true },
    "XTJ-5Q": { x: 590, y: 132, constellation: "6-CBBM", lawn: true },
    "JT2I-7": { x: 480, y: 132, constellation: "6-CBBM", lawn: true },
    "N-JK02": { x: 585, y: 172, constellation: "6-CBBM", lawn: true },

    // ===== LAWN 2Q-8WA (top-right) — EMPHASIZED =====
    "FB5U-I": { x: 768, y: 55, constellation: "2Q-8WA", lawn: true },
    "BZ-BCK": { x: 845, y: 55, constellation: "2Q-8WA", lawn: true },
    "J-OAH2": { x: 855, y: 18, constellation: "2Q-8WA", lawn: true },
    "O5-YNW": { x: 925, y: 55, constellation: "2Q-8WA", lawn: true },
    "86L-9F": { x: 955, y: 18, constellation: "2Q-8WA", lawn: true },
    "5-VFC6": { x: 818, y: 110, constellation: "2Q-8WA", lawn: true },
    "IUU3-L": { x: 1025, y: 55, constellation: "2Q-8WA", lawn: true },
    "S-LHPJ": { x: 1085, y: 18, constellation: "2Q-8WA", lawn: true },

    // ===== S4S-SD (below LAWN, center) =====
    "LE-67X": { x: 530, y: 192, constellation: "S4S-SD" },
    "L-GY1B": { x: 635, y: 205, constellation: "S4S-SD" },
    "74-DRC": { x: 590, y: 278, constellation: "S4S-SD" },
    "0S1-GI": { x: 725, y: 325, constellation: "S4S-SD" },
    "M3-H2Y": { x: 795, y: 285, constellation: "S4S-SD" },
    "O31W-6": { x: 842, y: 355, constellation: "S4S-SD" },
    "B1UE-J": { x: 935, y: 318, constellation: "S4S-SD" },

    // ===== 3NA-Z1 (left of center) =====
    "EPCD-D": { x: 358, y: 192, constellation: "3NA-Z1" },
    "L-TLFU": { x: 422, y: 212, constellation: "3NA-Z1" },
    "BM-VYZ": { x: 500, y: 212, constellation: "3NA-Z1" },
    "MN9P-A": { x: 485, y: 265, constellation: "3NA-Z1" },
    "RAI-0E": { x: 402, y: 265, constellation: "3NA-Z1" },
    "TA9T-P": { x: 318, y: 270, constellation: "3NA-Z1" },
    "Q-GICU": { x: 248, y: 295, constellation: "3NA-Z1" },

    // ===== 78-6RI (far right) =====
    "6V-D0E": { x: 1125, y: 132, constellation: "78-6RI" },
    "LS3-HP": { x: 1108, y: 172, constellation: "78-6RI" },
    "QX-4HO": { x: 1088, y: 215, constellation: "78-6RI" },
    "BVRQ-O": { x: 1058, y: 258, constellation: "78-6RI" },
    "SH6X-F": { x: 972, y: 258, constellation: "78-6RI" },
    "FBH-JN": { x: 1042, y: 292, constellation: "78-6RI" },

    // ===== U-HSM3 (south-center) =====
    "HPV-RJ": { x: 735, y: 435, constellation: "U-HSM3" },
    "C3J0-O": { x: 832, y: 450, constellation: "U-HSM3" },
    "WNM-V0": { x: 700, y: 505, constellation: "U-HSM3" },
    "6FS-CZ": { x: 618, y: 505, constellation: "U-HSM3" },
    "H7S-5I": { x: 505, y: 525, constellation: "U-HSM3" },
    "GSO-SR": { x: 675, y: 538, constellation: "U-HSM3" },
    "G-KCFT": { x: 848, y: 492, constellation: "U-HSM3" },
    "B3ZU-H": { x: 772, y: 542, constellation: "U-HSM3" },

    // ===== 2O-VY7 (far south) =====
    "A-YB15": { x: 672, y: 608, constellation: "2O-VY7" },
    "SG-3HY": { x: 822, y: 608, constellation: "2O-VY7" },
    "QZX-L9": { x: 792, y: 655, constellation: "2O-VY7" },
    "D-6PKO": { x: 732, y: 688, constellation: "2O-VY7" },
    "AU2V-J": { x: 635, y: 688, constellation: "2O-VY7" },
    "SY-0AM": { x: 722, y: 738, constellation: "2O-VY7" },

    // ===== 8UD2-J (far left) =====
    "G4-QU6": { x: 178, y: 338, constellation: "8UD2-J" },
    "V2-GZS": { x: 148, y: 378, constellation: "8UD2-J" },
    "42G-OB": { x: 98, y: 378, constellation: "8UD2-J" },
    "1S-SU1": { x: 25, y: 368, constellation: "8UD2-J" },
    "LEM-I1": { x: 45, y: 415, constellation: "8UD2-J" },
    "HD-HOZ": { x: 145, y: 422, constellation: "8UD2-J" },
    "ND-GL4": { x: 145, y: 468, constellation: "8UD2-J" },

    // ===== XPG-HE (south-west) =====
    "K95-9I": { x: 182, y: 522, constellation: "XPG-HE" },
    "M-75WN": { x: 242, y: 542, constellation: "XPG-HE" },
    "9-0QB7": { x: 415, y: 542, constellation: "XPG-HE" },
    "PNFW-O": { x: 278, y: 578, constellation: "XPG-HE" },
    "K76A-3": { x: 348, y: 562, constellation: "XPG-HE" },
    "HVGR-R": { x: 238, y: 655, constellation: "XPG-HE" },

    // ===== P-B2NE (center-west) =====
    "R1O-GN": { x: 315, y: 365, constellation: "P-B2NE" },
    "RQOO-U": { x: 400, y: 358, constellation: "P-B2NE" },
    "I2D3-5": { x: 378, y: 402, constellation: "P-B2NE" },
    "BGMZ-0": { x: 318, y: 408, constellation: "P-B2NE" },
    "GQ-7SP": { x: 258, y: 438, constellation: "P-B2NE" },
    "FZX-PU": { x: 368, y: 455, constellation: "P-B2NE" },
    "O9K-FT": { x: 288, y: 478, constellation: "P-B2NE" },

    // ===== NEIGHBOR: Vale of the Silent (top-left) =====
    "PX5-LR": { x: 275, y: 8, constellation: "neighbor", note: "Vale of the Silent" },
    "A3-RQ3": { x: 258, y: 48, constellation: "neighbor", note: "Vale of the Silent" },
    "9-GBPD": { x: 262, y: 100, constellation: "neighbor", note: "Vale of the Silent" },
    "LS-JEP": { x: 358, y: 72, constellation: "neighbor", note: "Vale of the Silent" },

    // ===== NEIGHBOR: Geminate (far left) =====
    "9-KWXC": { x: 72, y: 38, constellation: "neighbor", note: "Geminate" },
    "HJO-84": { x: 48, y: 115, constellation: "neighbor", note: "Geminate" },
    "P-E9GN": { x: 138, y: 112, constellation: "neighbor", note: "Geminate" },
    "4D9-66": { x: 42, y: 162, constellation: "neighbor", note: "Geminate" },
    "L-TOFR": { x: 132, y: 160, constellation: "neighbor", note: "Geminate" },
    "Q-TBHW": { x: 42, y: 250, constellation: "neighbor", note: "Geminate" },
    "9P4O-F": { x: 42, y: 335, constellation: "neighbor", note: "Geminate" },

    // ===== NEIGHBOR: Etherium Reach (scattered south/east) =====
    "AID-9T": { x: 712, y: 192, constellation: "neighbor", note: "Etherium Reach" },
    "TZ-74M": { x: 478, y: 462, constellation: "neighbor", note: "Etherium Reach" },
    "FB-MPY": { x: 578, y: 608, constellation: "neighbor", note: "Etherium Reach" },
    "J7M-3W": { x: 838, y: 738, constellation: "neighbor", note: "Etherium Reach" },

    // ===== NEIGHBOR: Malpais (right border) =====
    "V3P-AZ": { x: 1062, y: 368, constellation: "neighbor", note: "Malpais" },
    "7-YHRX": { x: 995, y: 438, constellation: "neighbor", note: "Malpais" },
    "Z-EKCY": { x: 885, y: 655, constellation: "neighbor", note: "Malpais" },
};

// ============ Subway Map Layout — abstract metro-style (same systems, new positions) ============
// LAWN systems: generous spacing (100px), strict 0/45/90° angles
// TKE systems: compact clusters (35px spacing)
// Neighbor systems: minimal, at edges
const MAP_LAYOUT_SUBWAY = {
    // ===== LAWN 6-CBBM (Green Line, left wing) — UNCHANGED =====
    "UDVW-O": { x: 300, y: 20, constellation: "6-CBBM", lawn: true },
    "UJXC-B": { x: 400, y: 120, constellation: "6-CBBM", lawn: true },
    "F48K-D": { x: 600, y: 120, constellation: "6-CBBM", lawn: true },
    "1-KCSA": { x: 500, y: 220, constellation: "6-CBBM", lawn: true },
    "XTJ-5Q": { x: 500, y: 320, constellation: "6-CBBM", lawn: true },
    "JT2I-7": { x: 400, y: 320, constellation: "6-CBBM", lawn: true },
    "N-JK02": { x: 600, y: 420, constellation: "6-CBBM", lawn: true },

    // ===== LAWN 2Q-8WA (Green Line, right wing) — UNCHANGED =====
    "FB5U-I": { x: 700, y: 120, constellation: "2Q-8WA", lawn: true },
    "BZ-BCK": { x: 850, y: 120, constellation: "2Q-8WA", lawn: true },
    "J-OAH2": { x: 850, y: 20, constellation: "2Q-8WA", lawn: true },
    "O5-YNW": { x: 1000, y: 120, constellation: "2Q-8WA", lawn: true },
    "86L-9F": { x: 1000, y: 20, constellation: "2Q-8WA", lawn: true },
    "5-VFC6": { x: 750, y: 220, constellation: "2Q-8WA", lawn: true },
    "IUU3-L": { x: 1100, y: 120, constellation: "2Q-8WA", lawn: true },
    "S-LHPJ": { x: 1100, y: 20, constellation: "2Q-8WA", lawn: true },

    // ===== S4S-SD (Shifted down +35px) =====
    "L-GY1B": { x: 600, y: 500, constellation: "S4S-SD" },
    "LE-67X": { x: 530, y: 500, constellation: "S4S-SD" },
    "74-DRC": { x: 670, y: 535, constellation: "S4S-SD" },
    "0S1-GI": { x: 730, y: 535, constellation: "S4S-SD" },
    "M3-H2Y": { x: 790, y: 535, constellation: "S4S-SD" },
    "O31W-6": { x: 730, y: 595, constellation: "S4S-SD" },
    "B1UE-J": { x: 850, y: 535, constellation: "S4S-SD" },

    // ===== 78-6RI (Shifted down +35px) =====
    "FBH-JN": { x: 910, y: 535, constellation: "78-6RI" },
    "SH6X-F": { x: 910, y: 495, constellation: "78-6RI" },
    "BVRQ-O": { x: 970, y: 535, constellation: "78-6RI" },
    "QX-4HO": { x: 1030, y: 535, constellation: "78-6RI" },
    "LS3-HP": { x: 1090, y: 535, constellation: "78-6RI" },
    "6V-D0E": { x: 1150, y: 535, constellation: "78-6RI" },

    // ===== 3NA-Z1 (Shifted down +35px) =====
    "MN9P-A": { x: 610, y: 585, constellation: "3NA-Z1" },
    "BM-VYZ": { x: 550, y: 585, constellation: "3NA-Z1" },
    "L-TLFU": { x: 550, y: 625, constellation: "3NA-Z1" },
    "EPCD-D": { x: 490, y: 625, constellation: "3NA-Z1" },
    "RAI-0E": { x: 610, y: 645, constellation: "3NA-Z1" },
    "TA9T-P": { x: 550, y: 675, constellation: "3NA-Z1" },
    "Q-GICU": { x: 490, y: 675, constellation: "3NA-Z1" },

    // ===== U-HSM3 (Shifted down +35px) =====
    "C3J0-O": { x: 730, y: 655, constellation: "U-HSM3" },
    "WNM-V0": { x: 730, y: 715, constellation: "U-HSM3" },
    "HPV-RJ": { x: 670, y: 715, constellation: "U-HSM3" },
    "G-KCFT": { x: 790, y: 715, constellation: "U-HSM3" },
    "6FS-CZ": { x: 670, y: 775, constellation: "U-HSM3" },
    "H7S-5I": { x: 610, y: 775, constellation: "U-HSM3" },
    "GSO-SR": { x: 730, y: 775, constellation: "U-HSM3" },
    "B3ZU-H": { x: 790, y: 775, constellation: "U-HSM3" },

    // ===== 2O-VY7 (Shifted down +35px) =====
    "SG-3HY": { x: 850, y: 715, constellation: "2O-VY7" },
    "A-YB15": { x: 910, y: 715, constellation: "2O-VY7" },
    "QZX-L9": { x: 850, y: 775, constellation: "2O-VY7" },
    "D-6PKO": { x: 910, y: 775, constellation: "2O-VY7" },
    "AU2V-J": { x: 970, y: 775, constellation: "2O-VY7" },
    "SY-0AM": { x: 910, y: 835, constellation: "2O-VY7" },

    // ===== 8UD2-J (Shifted down +35px) =====
    "G4-QU6": { x: 430, y: 675, constellation: "8UD2-J" },
    "V2-GZS": { x: 370, y: 675, constellation: "8UD2-J" },
    "42G-OB": { x: 310, y: 675, constellation: "8UD2-J" },
    "1S-SU1": { x: 250, y: 675, constellation: "8UD2-J" },
    "LEM-I1": { x: 310, y: 735, constellation: "8UD2-J" },
    "HD-HOZ": { x: 370, y: 735, constellation: "8UD2-J" },
    "ND-GL4": { x: 370, y: 795, constellation: "8UD2-J" },

    // ===== P-B2NE (Shifted down +35px) =====
    "R1O-GN": { x: 490, y: 735, constellation: "P-B2NE" },
    "RQOO-U": { x: 550, y: 735, constellation: "P-B2NE" },
    "I2D3-5": { x: 550, y: 795, constellation: "P-B2NE" },
    "BGMZ-0": { x: 490, y: 795, constellation: "P-B2NE" },
    "GQ-7SP": { x: 550, y: 855, constellation: "P-B2NE" },
    "FZX-PU": { x: 610, y: 855, constellation: "P-B2NE" },
    "O9K-FT": { x: 550, y: 915, constellation: "P-B2NE" },

    // ===== XPG-HE (Shifted down +35px) =====
    "K95-9I": { x: 370, y: 855, constellation: "XPG-HE" },
    "M-75WN": { x: 430, y: 855, constellation: "XPG-HE" },
    "9-0QB7": { x: 490, y: 855, constellation: "XPG-HE" },
    "HVGR-R": { x: 430, y: 915, constellation: "XPG-HE" },
    "PNFW-O": { x: 370, y: 915, constellation: "XPG-HE" },
    "K76A-3": { x: 310, y: 915, constellation: "XPG-HE" },

    // ===== NEIGHBOR: Vale of the Silent (Unchanged) =====
    "LS-JEP": { x: 170, y: 55, constellation: "neighbor", note: "Vale of the Silent" },
    "A3-RQ3": { x: 120, y: 55, constellation: "neighbor", note: "Vale of the Silent" },
    "9-GBPD": { x: 120, y: 105, constellation: "neighbor", note: "Vale of the Silent" },
    "PX5-LR": { x: 70, y: 20, constellation: "neighbor", note: "Vale of the Silent" },

    // ===== NEIGHBOR: Geminate (Shifted down +35px) =====
    "9-KWXC": { x: 100, y: 385, constellation: "neighbor", note: "Geminate" },
    "P-E9GN": { x: 100, y: 445, constellation: "neighbor", note: "Geminate" },
    "HJO-84": { x: 50, y: 445, constellation: "neighbor", note: "Geminate" },
    "4D9-66": { x: 50, y: 505, constellation: "neighbor", note: "Geminate" },
    "L-TOFR": { x: 100, y: 505, constellation: "neighbor", note: "Geminate" },
    "Q-TBHW": { x: 100, y: 575, constellation: "neighbor", note: "Geminate" },
    "9P4O-F": { x: 180, y: 675, constellation: "neighbor", note: "Geminate" },

    // ===== NEIGHBOR: Etherium Reach (Shifted down +35px) =====
    "AID-9T": { x: 670, y: 500, constellation: "neighbor", note: "Etherium Reach" },
    "TZ-74M": { x: 670, y: 855, constellation: "neighbor", note: "Etherium Reach" },
    "FB-MPY": { x: 970, y: 715, constellation: "neighbor", note: "Etherium Reach" },
    "J7M-3W": { x: 970, y: 835, constellation: "neighbor", note: "Etherium Reach" },

    // ===== NEIGHBOR: Malpais (Shifted down +35px) =====
    "V3P-AZ": { x: 910, y: 595, constellation: "neighbor", note: "Malpais" },
    "7-YHRX": { x: 790, y: 595, constellation: "neighbor", note: "Malpais" },
    "Z-EKCY": { x: 850, y: 835, constellation: "neighbor", note: "Malpais" },
};

// Gate connections — ALL verified from ESI /universe/stargates/ endpoint
const MAP_CONNECTIONS = [
    // ===== LAWN 6-CBBM internal (7 gates) =====
    ["UDVW-O", "UJXC-B", "internal"],
    ["UJXC-B", "1-KCSA", "internal"],
    ["UJXC-B", "F48K-D", "internal"],
    ["F48K-D", "1-KCSA", "internal"],
    ["1-KCSA", "XTJ-5Q", "internal"],
    ["XTJ-5Q", "JT2I-7", "internal"],
    ["XTJ-5Q", "N-JK02", "internal"],

    // ===== LAWN 2Q-8WA internal (7 gates) =====
    ["FB5U-I", "BZ-BCK", "internal"],
    ["BZ-BCK", "J-OAH2", "internal"],     // J-OAH2 dead-end
    ["BZ-BCK", "O5-YNW", "internal"],
    ["BZ-BCK", "5-VFC6", "internal"],      // 5-VFC6 dead-end
    ["O5-YNW", "86L-9F", "internal"],      // 86L-9F dead-end
    ["O5-YNW", "IUU3-L", "internal"],
    ["IUU3-L", "S-LHPJ", "internal"],      // S-LHPJ dead-end

    // ===== LAWN cross-constellation =====
    ["F48K-D", "FB5U-I", "cross"],         // 6-CBBM <-> 2Q-8WA

    // ===== LAWN external — ONLY 2 exits from LAWN space =====
    ["N-JK02", "L-GY1B", "cross"],         // Only gate from LAWN to rest of TKE
    ["UDVW-O", "LS-JEP", "regional"],      // Only gate from LAWN to Vale

    // ===== S4S-SD internal (6 gates) =====
    ["LE-67X", "L-GY1B", "internal"],
    ["L-GY1B", "74-DRC", "internal"],
    ["74-DRC", "0S1-GI", "internal"],
    ["0S1-GI", "M3-H2Y", "internal"],      // M3-H2Y dead-end
    ["0S1-GI", "O31W-6", "internal"],
    ["O31W-6", "B1UE-J", "internal"],

    // ===== S4S-SD cross-constellation =====
    ["74-DRC", "MN9P-A", "cross"],          // to 3NA-Z1
    ["B1UE-J", "FBH-JN", "cross"],          // to 78-6RI
    ["O31W-6", "C3J0-O", "cross"],          // to U-HSM3

    // ===== S4S-SD regional =====
    ["L-GY1B", "AID-9T", "regional"],       // to Etherium Reach
    ["O31W-6", "7-YHRX", "regional"],       // to Malpais
    ["B1UE-J", "V3P-AZ", "regional"],       // to Malpais

    // ===== 3NA-Z1 internal (7 gates) =====
    ["EPCD-D", "L-TLFU", "internal"],       // EPCD-D dead-end
    ["L-TLFU", "BM-VYZ", "internal"],
    ["L-TLFU", "MN9P-A", "internal"],
    ["BM-VYZ", "MN9P-A", "internal"],
    ["MN9P-A", "RAI-0E", "internal"],
    ["RAI-0E", "TA9T-P", "internal"],
    ["TA9T-P", "Q-GICU", "internal"],

    // ===== 3NA-Z1 cross-constellation =====
    ["Q-GICU", "G4-QU6", "cross"],          // to 8UD2-J
    ["Q-GICU", "R1O-GN", "cross"],          // to P-B2NE

    // ===== 78-6RI internal (5 gates) =====
    ["6V-D0E", "LS3-HP", "internal"],       // 6V-D0E dead-end
    ["LS3-HP", "QX-4HO", "internal"],
    ["QX-4HO", "BVRQ-O", "internal"],
    ["BVRQ-O", "FBH-JN", "internal"],
    ["FBH-JN", "SH6X-F", "internal"],       // SH6X-F dead-end

    // ===== U-HSM3 internal (10 gates) =====
    ["WNM-V0", "HPV-RJ", "internal"],       // HPV-RJ dead-end
    ["WNM-V0", "6FS-CZ", "internal"],
    ["WNM-V0", "GSO-SR", "internal"],
    ["WNM-V0", "C3J0-O", "internal"],
    ["WNM-V0", "G-KCFT", "internal"],
    ["WNM-V0", "B3ZU-H", "internal"],
    ["6FS-CZ", "H7S-5I", "internal"],
    ["B3ZU-H", "GSO-SR", "internal"],
    ["B3ZU-H", "G-KCFT", "internal"],
    ["C3J0-O", "G-KCFT", "internal"],

    // ===== U-HSM3 cross-constellation =====
    ["G-KCFT", "SG-3HY", "cross"],          // to 2O-VY7
    ["H7S-5I", "9-0QB7", "cross"],           // to XPG-HE

    // ===== 2O-VY7 internal (8 gates) =====
    ["A-YB15", "SG-3HY", "internal"],
    ["SG-3HY", "QZX-L9", "internal"],
    ["QZX-L9", "AU2V-J", "internal"],
    ["QZX-L9", "D-6PKO", "internal"],
    ["QZX-L9", "SY-0AM", "internal"],
    ["AU2V-J", "D-6PKO", "internal"],
    ["AU2V-J", "SY-0AM", "internal"],
    ["D-6PKO", "SY-0AM", "internal"],

    // ===== 2O-VY7 regional =====
    ["A-YB15", "FB-MPY", "regional"],        // to Etherium Reach
    ["SY-0AM", "J7M-3W", "regional"],        // to Etherium Reach
    ["QZX-L9", "Z-EKCY", "regional"],        // to Malpais

    // ===== 8UD2-J internal (8 gates) =====
    ["G4-QU6", "V2-GZS", "internal"],
    ["V2-GZS", "42G-OB", "internal"],
    ["V2-GZS", "HD-HOZ", "internal"],
    ["42G-OB", "HD-HOZ", "internal"],
    ["42G-OB", "LEM-I1", "internal"],
    ["HD-HOZ", "LEM-I1", "internal"],
    ["HD-HOZ", "ND-GL4", "internal"],
    ["LEM-I1", "ND-GL4", "internal"],
    ["LEM-I1", "1S-SU1", "internal"],

    // ===== 8UD2-J cross-constellation =====
    ["ND-GL4", "K95-9I", "cross"],           // to XPG-HE

    // ===== 8UD2-J regional =====
    ["1S-SU1", "9P4O-F", "regional"],        // to Geminate

    // ===== XPG-HE internal (8 gates) =====
    ["K95-9I", "M-75WN", "internal"],
    ["K95-9I", "HVGR-R", "internal"],
    ["M-75WN", "9-0QB7", "internal"],
    ["M-75WN", "PNFW-O", "internal"],
    ["M-75WN", "HVGR-R", "internal"],
    ["9-0QB7", "HVGR-R", "internal"],
    ["HVGR-R", "PNFW-O", "internal"],
    ["K76A-3", "PNFW-O", "internal"],        // K76A-3 dead-end

    // ===== P-B2NE internal (12 gates) =====
    ["R1O-GN", "I2D3-5", "internal"],
    ["R1O-GN", "RQOO-U", "internal"],
    ["R1O-GN", "BGMZ-0", "internal"],
    ["R1O-GN", "GQ-7SP", "internal"],
    ["I2D3-5", "RQOO-U", "internal"],
    ["I2D3-5", "BGMZ-0", "internal"],
    ["I2D3-5", "GQ-7SP", "internal"],
    ["I2D3-5", "FZX-PU", "internal"],
    ["BGMZ-0", "GQ-7SP", "internal"],
    ["GQ-7SP", "FZX-PU", "internal"],
    ["GQ-7SP", "O9K-FT", "internal"],
    ["FZX-PU", "O9K-FT", "internal"],

    // ===== P-B2NE regional =====
    ["FZX-PU", "TZ-74M", "regional"],        // to Etherium Reach

    // ===== Neighbor: Vale of the Silent internal =====
    ["PX5-LR", "A3-RQ3", "neighbor"],
    ["A3-RQ3", "9-GBPD", "neighbor"],
    ["A3-RQ3", "LS-JEP", "neighbor"],
    ["9-GBPD", "LS-JEP", "neighbor"],

    // ===== Neighbor: Geminate internal =====
    ["9-KWXC", "P-E9GN", "neighbor"],
    ["P-E9GN", "HJO-84", "neighbor"],
    ["P-E9GN", "L-TOFR", "neighbor"],
    ["HJO-84", "4D9-66", "neighbor"],
    ["4D9-66", "L-TOFR", "neighbor"],
    ["L-TOFR", "Q-TBHW", "neighbor"],
    ["Q-TBHW", "9P4O-F", "neighbor"],

    // ===== Cross-region: Geminate <-> Vale =====
    ["L-TOFR", "9-GBPD", "regional"],        // Geminate to Vale regional gate
];

const LAWN_SYSTEMS = ["UDVW-O", "UJXC-B", "F48K-D", "1-KCSA", "XTJ-5Q", "JT2I-7", "N-JK02", "FB5U-I", "BZ-BCK", "J-OAH2", "O5-YNW", "86L-9F", "5-VFC6", "IUU3-L", "S-LHPJ"];
const BORDER_SYSTEMS = ["UDVW-O", "N-JK02", "1S-SU1", "L-GY1B", "FZX-PU", "A-YB15", "SY-0AM", "B1UE-J", "O31W-6", "QZX-L9"];
