const { chromium } = require('playwright');

const connectionURL = 'wss://browser.zenrows.com?apikey=';

async function autoScroll(page) {
    await page.evaluate(async () => {
        await new Promise((resolve) => {
            let totalHeight = 0;
            const distance = 400;
            const timer = setInterval(() => {
                const scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;
                if (totalHeight >= scrollHeight - window.innerHeight) {
                    clearInterval(timer);
                    resolve();
                }
            }, 200);
        });
    });
}

(async () => {
    console.log('🚀 Connecting to ZenRows Scraping Browser...');
    const browser = await chromium.connectOverCDP(connectionURL);
    const context = browser.contexts()[0];
    const page = await context.newPage();

    const rawCookieString = 'your_Cookie';
    const cookieObjects = rawCookieString.split(';').map(pair => {
        const [name, ...valueParts] = pair.trim().split('=');
        if (!name || valueParts.length === 0) return null;
        return { name, value: valueParts.join('='), domain: '.jobsdb.com', path: '/' };
    }).filter(cookie => cookie !== null);

    await context.addCookies(cookieObjects);

    console.log('🔗 Navigating to profile...');
    await page.goto('https://th.jobsdb.com/th/profiles/oatsada-chatthong-z8m7lGd1pj', {
        waitUntil: 'domcontentloaded', timeout: 60000
    });

    console.log('⏳ Waiting a few seconds for the page to settle...');
    await page.waitForTimeout(3000);

    console.log('🔄 Scrolling down the page to trigger lazy-loaded content...');
    await autoScroll(page);

    try {
        console.log('🚀 Extracting structured data from the DOM...');

        const profileData = await page.evaluate(() => {
            const bodyText = document.body.innerText;
            const lines = bodyText.split('\n').map(l => l.trim()).filter(l => l.length > 0);

            let data = {
                Name: "Not Found",
                CurrentRole: "Not Found",
                Location: "Not Found",
                WorkExperience: [],
                Education: [],
                Skills: []
            };

            const anchorIdx = lines.findIndex(l => l === "ประวัติการทำงาน" || l === "การศึกษา");

            if (anchorIdx !== -1) {
                const lineMinus1 = lines[anchorIdx - 1];
                const lineMinus2 = lines[anchorIdx - 2];
                const lineMinus3 = lines[anchorIdx - 3];

                data.Location = lineMinus1;

                if (lineMinus3 && lineMinus3.length <= 2) {
                    data.Name = lineMinus2;
                    data.CurrentRole = "Not Found";
                } else {
                    data.Name = lineMinus3;
                    data.CurrentRole = lineMinus2;
                }
            }

            const extractSection = (startKeyword, endKeywords) => {
                const startIdx = lines.indexOf(startKeyword);
                if (startIdx === -1) return [];

                let endIdx = lines.length;
                for (let i = startIdx + 1; i < lines.length; i++) {
                    if (endKeywords.includes(lines[i])) {
                        endIdx = i;
                        break;
                    }
                }
                return lines.slice(startIdx + 1, endIdx);
            };

            data.WorkExperience = extractSection("ประวัติการทำงาน", [
                "การศึกษา", "ทักษะ", "รายละเอียดโปรไฟล์ ทักษะ และตัวกรองในการค้นหา", "เข้าสู่ระบบเพื่อดูข้อมูลเพิ่มเติม"
            ]);

            data.Education = extractSection("การศึกษา", [
                "ทักษะ", "รายละเอียดโปรไฟล์ ทักษะ และตัวกรองในการค้นหา", "เข้าสู่ระบบเพื่อดูข้อมูลเพิ่มเติม", "ประวัติการทำงาน"
            ]);

            data.Skills = extractSection("ทักษะ", [
                "รายละเอียดโปรไฟล์ ทักษะ และตัวกรองในการค้นหา", "เข้าสู่ระบบเพื่อดูข้อมูลเพิ่มเติม", "ประวัติการทำงาน", "การศึกษา"
            ]);

            if (data.Education.length === 0) data.Education = "Hidden or Not Found (Update Cookies to Login)";
            if (data.Skills.length === 0) data.Skills = "Hidden or Not Found (Update Cookies to Login)";

            return data;
        });

        console.log('\n✅ SUCCESS! Structured JSON Data:');
        console.log(JSON.stringify(profileData, null, 2));

        // 📸 คำสั่งใหม่: ถ่ายรูปหน้าจอเก็บไว้หลังทำทุกอย่างเสร็จแล้ว
        //console.log('\n📸 Taking a full-page screenshot...');
        //await page.screenshot({ path: 'final_screenshot.png', fullPage: true });
        //console.log('✅ Screenshot saved as "final_screenshot.png"');

    } catch (error) {
        console.error('❌ ERROR extracting data:', error.message);
    }

    await browser.close();
    console.log('👋 Browser connection closed.');
})();