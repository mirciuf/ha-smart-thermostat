# 🌡️ Smart Thermostat pentru Home Assistant

Un termostat inteligent complet pentru Home Assistant, cu control independent pentru încălzire și răcire, construit de la zero fără dependențe externe.

---

## ✅ Funcționalități

- **Control încălzire** — switch robinet calorifer
- **Control răcire** — switch AC sau scenă HA (scene.ac_cool / scene.ac_off)
- **Histereza configurabilă** — bandă de toleranță ±X°C în jurul temperaturii țintă
- **Senzor temperatură exterioară** — oprește automat încălzirea când afară e mai cald decât pragul setat
- **2 senzori geam/ușă** — oricare deschis oprește termostatul
- **Senzori indisponibili** — ignorați automat cu notificare HA (nu opresc termostatul)
- **Preseturi configurabile** — Acasă, Plecat, Noapte etc. cu temperaturi personalizate
- **Card Lovelace custom** — cadran circular, responsive, compatibil cu orice temă HA
- **Thumb draggabil** — modifici temperatura direct pe cadran
- **Persistarea stării** — modul și temperatura țintă supraviețuiesc la restart HA
- **Device info** — apare ca device în HA (compatibil cu automatizări prin device_id)

---

## 📦 Instalare

### Metoda 1: HACS (recomandat)

**Integrare:**
1. HACS → Integrări → ⋮ → Custom repositories
2. URL: `https://github.com/mirciuf/ha-smart-thermostat`
3. Categorie: **Integration** → Add
4. Caută **Smart Thermostat** → Download
5. Restart Home Assistant

**Card Lovelace:**
1. HACS → Frontend → ⋮ → Custom repositories
2. URL: `https://github.com/mirciuf/ha-smart-thermostat`
3. Categorie: **Dashboard** → Add
4. Caută **Smart Thermostat Card** → Download
5. Hard refresh browser (`Ctrl+Shift+R`)

### Metoda 2: Manual

1. Copiați folderul `custom_components/smart_thermostat/` în `/config/custom_components/`
2. Copiați folderul `www/smart-thermostat-card/` în `/config/www/`
3. Restart Home Assistant
4. Mergeți la **Setări → Dashboard → Resurse → +** și adăugați:
   - URL: `/local/smart-thermostat-card/smart-thermostat-card.js`
   - Tip: `JavaScript Module`

---

## ⚙️ Configurare

### Pasul 1 — Adăugați integrarea

**Setări → Dispozitive & Servicii → + Adaugă Integrare → Smart Thermostat**

| Câmp | Descriere | Exemplu |
|------|-----------|---------|
| **Numele termostatului** | Nume descriptiv | `Termostat Living` |
| **Senzor temperatură interior** | Senzorul din cameră | `sensor.living_temperature` |
| **Switch radiator** | Controlează robinetul caloriferului | `switch.robinet_living` |
| **Switch AC** | Controlează AC-ul (opțional) | `switch.ac_living` |
| **Scenă AC pornire răcire** | Alternativă la switch AC | `scene.ac_cool` |
| **Scenă AC oprire răcire** | Alternativă la switch AC | `scene.ac_off` |
| **Senzor geam 1** | Oprește termostatul când e deschis | `binary_sensor.geam_living` |
| **Senzor geam 2** | Al doilea senzor (opțional) | `binary_sensor.usa_balcon` |
| **Senzor temperatură exterior** | Oprește încălzirea la temperaturi mari | `sensor.outdoor_temperature` |
| **Temperatura țintă** | Setpoint inițial | `21.0` |
| **Histereza** | Banda de toleranță ±X°C | `0.5` |
| **Prag temperatură exterior** | Peste această valoare, încălzirea se oprește | `20.0` |
| **Temperatura minimă** | Limita inferioară setabilă | `5.0` |
| **Temperatura maximă** | Limita superioară setabilă | `35.0` |

> **Notă:** Folosești fie **Switch AC** fie **Scenă pornire + Scenă oprire** — nu ambele simultan.

### Pasul 2 — Adăugați cardul în dashboard

```yaml
type: custom:smart-thermostat-card
entity: climate.termostat_living
```

---

## 🔧 Logica de control

### Mod Căldură (Heat)
```
Pornește radiatorul când:  temp_curentă ≤ temp_țintă - histereza
Oprește radiatorul când:   temp_curentă ≥ temp_țintă + histereza
```
**Blocat dacă:**
- Temperatura exterioară > prag exterior
- Oricare senzor de geam e deschis

### Mod Răcire (Cool)
```
Pornește AC când:  temp_curentă ≥ temp_țintă + histereza
Oprește AC când:   temp_curentă ≤ temp_țintă - histereza
```
**Blocat dacă:**
- Oricare senzor de geam e deschis

### Exemplu cu histereza = 0.5°C și țintă = 21°C
```
Pornire căldură:  temp < 20.5°C
Oprire căldură:   temp > 21.5°C
Pornire răcire:   temp > 21.5°C
Oprire răcire:    temp < 20.5°C
```

---

## 🪟 Senzori geam indisponibili

Dacă un senzor de geam devine `unavailable` (baterie descărcată, pierdere semnal):
- Termostatul **continuă să funcționeze normal** — senzorul e ignorat
- Se creează o **notificare în HA** că senzorul e offline
- Când senzorul revine online — notificarea dispare automat

Aceasta previne situații nedorite (ex: -30°C afară, senzorul fără baterii → termostatul nu se oprește).

---

## 🎛️ Preseturi

Din butonul ⚙️ → **Gestionează preseturi** poți adăuga preseturi cu nume și temperatură:

| Preset | Temperatură |
|--------|-------------|
| Acasă | 21°C |
| Noapte | 18°C |
| Plecat | 16°C |
| Confort | 23°C |

Când selectezi un preset din card, temperatura țintă se schimbă automat. Când modifici manual temperatura, termostatul iese din preset (→ Manual).

---

## 🃏 Cardul Lovelace

### Indicatori vizuali

| Indicator | Semnificație |
|-----------|-------------|
| 🪟 Albastru | Geam/ușă deschisă — termostatul oprit |
| ☀️ Portocaliu | Temperatura exterioară > prag — încălzirea oprită |
| 🔴 Radiator roșu | Încălzire activă (switch ON) |
| 🟠 Radiator portocaliu | Mod heat, în așteptare |
| ❄️ Fulg albastru | Răcire activă |
| Arc gri | Termostat blocat sau oprit |

### Modificare temperatură
- **Butoane − / +** — pași de 0.5°C
- **Drag pe cadran** — apucă bulina albă și trage pe arc

---

## 🔄 Butonul ⚙️ — Opțiuni disponibile

| Opțiune | Descriere |
|---------|-----------|
| Modifică configurația | Schimbă senzori și switch-uri |
| Modifică parametrii | Temperatură, histereza, prag exterior, min/max |
| Gestionează preseturi | Adaugă sau șterge preseturi |

---

## 🏠 Integrare cu automatizări

Fiecare termostat apare ca **device** în HA (Manufacturer: TopTech Labs), deci poate fi folosit în automatizări prin `device_id` sau `entity_id`:

```yaml
# Exemplu: setare temperatură când pleci acasă
action: climate.set_temperature
target:
  entity_id:
    - climate.termostat_living
    - climate.termostat_dormitor
data:
  temperature: 18

# Exemplu: schimbare mod
action: climate.set_hvac_mode
target:
  entity_id: climate.termostat_living
data:
  hvac_mode: heat  # heat / cool / off

# Exemplu: activare preset
action: climate.set_preset_mode
target:
  entity_id: climate.termostat_living
data:
  preset_mode: "Noapte"
```

---

## 📁 Structura fișierelor

```
ha-smart-thermostat/
├── custom_components/
│   └── smart_thermostat/
│       ├── __init__.py
│       ├── climate.py          ← logica termostatului
│       ├── config_flow.py      ← interfața de configurare
│       ├── const.py            ← constante
│       ├── manifest.json
│       ├── strings.json
│       ├── brand/              ← logo și iconițe
│       └── translations/       ← română + engleză
├── www/
│   └── smart-thermostat-card/
│       └── smart-thermostat-card.js  ← cardul Lovelace
├── hacs.json
└── README.md
```

---

## 📝 Licență

MIT License — utilizare liberă și modificare

---

*Dezvoltat cu ❤️ folosind Claude AI*
