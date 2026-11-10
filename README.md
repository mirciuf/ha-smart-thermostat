# 🌡️ Smart Thermostat pentru Home Assistant

Un termostat inteligent complet pentru Home Assistant, cu control independent pentru încălzire și răcire, construit de la zero fără dependențe externe.

---

## ✅ Funcționalități

- **Control încălzire** — switch robinet calorifer
- **Control răcire, în 3 variante** — switch AC, scene HA (pornire/oprire) sau o entitate `climate` (AC nativ sau IR)
- **Protecție compresor AC** — timp minim de funcționare înainte de oprire (varianta Climate Entity)
- **AC partajat între termostate** — AC-ul nu se oprește cât timp un alt termostat încă are nevoie de răcire
- **Histereza configurabilă** — bandă de toleranță ±X°C în jurul temperaturii țintă
- **Pas de temperatură configurabil** — 0.1 / 0.2 / 0.5 / 1.0°C
- **Senzor temperatură exterioară** — oprește automat încălzirea când afară e mai cald decât pragul setat
- **2 senzori geam/ușă** — oricare deschis oprește termostatul
- **Senzori indisponibili** — ignorați automat, cu notificare în HA (nu opresc termostatul)
- **Preseturi configurabile** — Acasă, Plecat, Noapte etc. cu temperaturi personalizate
- **Card Lovelace custom** — cadran circular, responsive, compatibil cu orice temă HA
- **Thumb draggabil** — modifici temperatura direct pe cadran
- **Persistarea stării** — modul și temperatura țintă supraviețuiesc la restart HA
- **Device info** — apare ca device în HA (compatibil cu automatizări prin `device_id`)
- **Interfață bilingvă** — engleză și română

---

## 📦 Instalare

Integrarea se instalează în folderul:

```
/config/custom_components/toptech_smart_thermostat/
```

> Pe Home Assistant OS / Supervised, `/config` este același lucru cu `/homeassistant`.

### Integrarea — metoda 1: HACS (recomandat)

1. HACS → Integrări → ⋮ → **Custom repositories**
2. URL: `https://github.com/mirciuf/ha-smart-thermostat`
3. Categorie: **Integration** → Add
4. Caută **Smart Thermostat** → Download
5. Restart Home Assistant

HACS creează singur folderul `toptech_smart_thermostat`.

### Integrarea — metoda 2: manual

1. Copiați folderul `custom_components/toptech_smart_thermostat/` în `/config/custom_components/`
2. Restart Home Assistant

### Cardul Lovelace (instalare manuală)

HACS acceptă o singură categorie pe repository, iar acesta este înregistrat ca **Integration**. Din acest motiv cardul se instalează manual:

1. Copiați folderul `www/smart-thermostat-card/` în `/config/www/`
2. Mergeți la **Setări → Dashboard → ⋮ → Resurse → + Adaugă resursă**:
   - URL: `/local/smart-thermostat-card/smart-thermostat-card.js`
   - Tip: **JavaScript Module**
3. Hard refresh în browser (`Ctrl+Shift+R`)

---

## ⚠️ Actualizare de la versiunea 1.6.0 sau mai veche

Începând cu **v1.7.0**, integrarea s-a mutat din `smart_thermostat` în `toptech_smart_thermostat`. Home Assistant leagă fiecare integrare de numele folderului, așa că vechea configurație nu se mută automat. Pași:

1. Notați setările fiecărui termostat (senzori, switch-uri, preseturi).
2. **Setări → Dispozitive & Servicii → Smart Thermostat → ⋮ → Șterge** (pentru fiecare termostat).
3. Ștergeți vechiul folder `/config/custom_components/smart_thermostat/`.
4. Instalați noua versiune (vezi mai sus) și restartați Home Assistant.
5. Adăugați din nou termostatele, cu **exact aceleași nume** ca înainte, ca să păstrați `entity_id`-urile (`climate.termostat_living` etc.). Cardurile și automatizările continuă atunci să funcționeze.

---

## ⚙️ Configurare

### Pasul 1 — Adăugați integrarea

**Setări → Dispozitive & Servicii → + Adaugă Integrare → Smart Thermostat**

| Câmp | Descriere | Exemplu |
|------|-----------|---------|
| **Numele termostatului** | Nume descriptiv | `Termostat Living` |
| **Senzor temperatură interior** | Senzorul din cameră | `sensor.living_temperature` |
| **Switch radiator** | Controlează robinetul caloriferului | `switch.robinet_living` |
| **Tip răcire** | Fără răcire / Switch / Scenă / Climate Entity | `Climate Entity` |
| **Switch AC** | Doar pentru tipul *Switch* | `switch.ac_living` |
| **Scenă pornire / oprire AC** | Doar pentru tipul *Scenă* | `scene.ac_cool` / `scene.ac_off` |
| **Climate entity AC** | Doar pentru tipul *Climate Entity* | `climate.ac_living` |
| **Temperatură fixă AC la pornire** | Temperatura setată pe AC când începe răcirea (16–30°C) | `18.0` |
| **Funcționare minimă AC** | Minute minime de funcționare înainte de oprire, 0–120 (0 = fără protecție) | `10` |
| **Senzor geam 1 / 2** | Oprește termostatul când e deschis (opțional) | `binary_sensor.geam_living` |
| **Senzor temperatură exterior** | Oprește încălzirea la temperaturi mari (opțional) | `sensor.outdoor_temperature` |
| **Temperatura țintă** | Setpoint inițial | `21.0` |
| **Histereza** | Banda de toleranță ±X°C (0–2) | `0.5` |
| **Prag temperatură exterior** | Peste această valoare, încălzirea se oprește | `20.0` |
| **Temperatura minimă / maximă** | Limitele setabile | `5.0` / `35.0` |
| **Pasul de temperatură** | Pasul butoanelor +/− și al cadranului | `0.5` |

> **Notă:** Alegi **un singur tip de răcire**. Câmpurile care nu aparțin tipului ales sunt ignorate și golite automat la salvare.

### Pasul 2 — Adăugați cardul în dashboard

```yaml
type: custom:smart-thermostat-card
entity: climate.termostat_living
```

---

## ❄️ Tipuri de răcire

| Tip | Cum funcționează |
|-----|------------------|
| **Switch** | Pornește / oprește un switch care alimentează sau comandă AC-ul |
| **Scenă** | Activează o scenă de pornire răcire și una de oprire (ex: AC cu telecomandă IR) |
| **Climate Entity** | Pune AC-ul pe modul `cool` la temperatura fixă setată și îl oprește cu `off`, respectând timpul minim de funcționare |

**Protecția compresorului (Climate Entity):** dacă termostatul cere oprirea AC-ului înainte de expirarea timpului minim, oprirea este amânată automat până la expirare. Dacă între timp condițiile se schimbă (de exemplu răcirea e cerută din nou), oprirea programată este anulată.

**AC partajat:** dacă mai multe termostate folosesc același AC (aceeași scenă sau aceeași entitate climate), AC-ul se oprește doar când niciunul nu mai are nevoie de răcire.

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
- **Butoane − / +** — pasul setat în configurare (implicit 0.5°C)
- **Drag pe cadran** — apucă bulina albă și trage pe arc

---

## 🔄 Butonul ⚙️ — Opțiuni disponibile

| Opțiune | Descriere |
|---------|-----------|
| Modifică configurația | Schimbă senzori, switch-uri și tipul de răcire |
| Modifică parametrii | Temperatură, histereza, prag exterior, min/max, pas |
| Gestionează preseturi | Adaugă sau șterge preseturi |

---

## 🏠 Integrare cu automatizări

Fiecare termostat apare ca **device** în HA (Manufacturer: TopTech Labs), deci poate fi folosit în automatizări prin `device_id` sau `entity_id`:

```yaml
# Exemplu: setare temperatură când pleci de acasă
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
│   └── toptech_smart_thermostat/
│       ├── __init__.py
│       ├── climate.py          ← logica termostatului
│       ├── config_flow.py      ← interfața de configurare
│       ├── const.py            ← constante
│       ├── manifest.json
│       ├── strings.json
│       ├── brand/              ← logo și iconițe (icon.png, icon@2x.png)
│       └── translations/       ← engleză + română
├── www/
│   └── smart-thermostat-card/
│       └── smart-thermostat-card.js  ← cardul Lovelace
├── hacs.json
└── README.md
```

---

## 📝 Istoric versiuni

- **1.7.0** — folderul integrării a fost redenumit în `toptech_smart_thermostat`; `en.json` tradus în engleză; texte lipsă adăugate în traduceri; README actualizat
- **1.6.0** — răcire prin climate entity cu protecție de funcționare minimă; pas de temperatură configurabil; logică AC partajată
- **1.0.0** — lansare inițială

---

## 📝 Licență

MIT License — utilizare liberă și modificare

---

*Dezvoltat cu ❤️ folosind Claude AI*
