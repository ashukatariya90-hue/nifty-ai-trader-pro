# V5.18 — Angel One registration preparation

इस अपडेट में Angel One SmartAPI registration form के लिए project की ओर से तय हो सकने वाले विवरण और deployment पर निर्भर विवरण अलग-अलग दर्ज किए गए हैं।

- App Name: NIFTY AI TRADER PRO (suggested label)
- Redirect URL: अभी निर्धारित नहीं; वास्तविक HTTPS callback deployment और provider contract की पुष्टि आवश्यक है।
- Post back URL: अभी निर्धारित नहीं; optional और provider requirement पर निर्भर।
- Primary Static IP: अभी उपलब्ध नहीं; deployed backend की verified fixed outbound IP आवश्यक है।
- Secondary Static IP: अभी उपलब्ध नहीं; केवल तभी जब hosting provider दूसरा fixed egress IP दे।

यह update registration, authentication या live feed connection नहीं करता। Angel One adapter OFFLINE_NOT_CONFIGURED ही रहेगा। Simulated/historical data और paper-only mode अलग रहेंगे। अधिक जानकारी के लिए `ANGEL_ONE_APP_REGISTRATION_PREPARATION_V5_18.md` देखें।
