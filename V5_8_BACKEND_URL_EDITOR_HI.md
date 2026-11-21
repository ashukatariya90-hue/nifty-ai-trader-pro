# V5.8 — Backend URL editor (Hindi)

- Integration tab mein HTTPS backend URL edit karne ka field add kiya gaya hai.
- `SAVE BACKEND URL` dabane par URL isi Android device par save hota hai (SharedPreferences).
- App dobara kholne par saved URL bana rahega.
- Default URL: `https://nifty-ai-trader-pro.onrender.com`
- `CHECK BACKEND CONNECTION` saved URL ke `/api/v5/integration-status` endpoint ko check karta hai.
- Yeh sirf backend reachability check hai; live market feed, broker login ya order execution enable nahi karta. App paper/educational mode mein hi hai.

## Build
GitHub Actions workflow Java 17 aur Gradle 8.7 se debug APK banata hai. `API_BASE_URL` repository variable blank ho tab bhi default Render URL set rahega.

## Note
Is environment mein Android Gradle build run nahi ho saka (Gradle installed nahi tha). GitHub Actions par build result verify karna zaroori hai.
