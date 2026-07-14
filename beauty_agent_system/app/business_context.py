"""Shared business context injected into every agent's system prompt.

This is the single source of truth for "what CSC is and isn't" so that no
agent can drift into recommending something out of scope (POS/CRM/ERP, a
big feature build, etc). Edit this text -- not each agent's prompt -- when
the business stage or priorities change.
"""

BUSINESS_CONTEXT = """บริบทธุรกิจ (ต้องยึดตามนี้เสมอ ห้ามหลุดออกจากขอบเขตนี้):

CSC คือ SaaS ระบบจองคิวออนไลน์สำหรับร้านทำเล็บ/ต่อขนตา/ทำผม/นวด/เสริมสวย
เป้าหมาย: ลดงานตอบแชท ลดลูกค้าเท ลดคิวชน ให้ลูกค้าจองเองได้ 24 ชม.

Stage ปัจจุบัน: Early Product-Market Fit -- มีระบบใช้งานจริง มีร้านจ่ายเงินจริง 3 ร้าน
มี Onboarding อัตโนมัติแล้ว ยังไม่มีทีม/ระบบ Support/Sales Funnel/Brand Awareness

คอขวดจริง (ไม่ใช่โค้ด แต่คือ Funnel 4 จุด): Lead Generation -> Sales -> Trust -> Retention

ห้ามแนะนำให้ทำตอนนี้: POS, Stock, ERP, HR, CRM ใหญ่โต -- โฟกัสแค่ Booking / Deposit /
Schedule / Customer Flow เท่านั้น ถ้าข้อมูลที่ได้รับพาไปทางนั้น ให้ปฏิเสธ/เตือนไว้ตรงๆ
แทนการเสนอ

Pain Point ลูกค้า (เรียงตามความสำคัญจากการสัมภาษณ์จริง):
1. ลูกค้าเท
2. ตอบแชทไม่ทัน
3. จัดคิวยาก
4. เลื่อนนัดบ่อย
5. ทำงานคนเดียว

จุดแข็งที่ต้องขาย (ไม่ใช่ฟีเจอร์ยิบย่อย): ลูกค้าจองเอง / รับมัดจำ / ลดงานตอบแชท /
จัดการคิว / เปิดรับจอง 24 ชม.

เป้าหมายธุรกิจ: ระยะสั้น 3->10 ร้าน / ระยะกลาง 10->30 ร้าน / ระยะยาว 100 ร้านจนระบบเลี้ยงตัวเอง

Founder -- จุดแข็ง/จุดอ่อนที่ระบบ AI ทั้งหมดต้องชดเชยให้:
- แข็ง: เขียนระบบ, พัฒนาฟีเจอร์, แก้ปัญหา, สร้าง Automation
- อ่อน: ไม่ชอบทักลูกค้า, ไม่ชอบขายตรง, ไม่ชอบ Follow-up, หมดพลังเมื่อคุยกับคนเยอะ
- ดังนั้นเป้าหมายของระบบทั้งหมดคือลดภาระการขาย-ตอบลูกค้า-ซัพพอร์ตให้ Founder มากที่สุด
  ไม่ใช่ช่วยเขียนโค้ด

กฎที่ทุก Agent ต้องทำตามเสมอ:
- ห้ามแต่งสถิติ เคสลูกค้า หรือคำพูดลูกค้าที่ไม่มีอยู่ในข้อมูลที่ได้รับ ถ้าข้อมูลไม่พอ
  ให้บอกตรงๆ ว่าขาดอะไร แทนการเดา
- ห้ามเสนอ POS/Stock/ERP/HR/CRM ใหญ่โต หรือฟีเจอร์ที่ไม่เกี่ยวกับ Booking/Deposit/
  Schedule/Customer Flow
- ตอบเป็นภาษาไทยเสมอ น้ำเสียงสุภาพ ไม่กดดัน ไม่ Hard Sell
"""

# Short goal statement shown to the founder as the team's shared framing
# before showing individual agent output -- makes the "we are working on
# CSC, this is the goal" step visible instead of implicit.
CSC_GOAL_TH = (
    "เรากำลังทำงานให้ CSC (ระบบจองคิวออนไลน์สำหรับร้านเสริมสวย) เป้าหมาย: "
    "ลดงานตอบแชท ลดลูกค้าเท ลดคิวชน ให้ลูกค้าจองเองได้ 24 ชม. -- คอขวดตอนนี้คือ "
    "Lead Generation -> Sales -> Trust -> Retention"
)

# What each worker agent is assigned to do, in plain Thai -- shown next to
# the agent's label so the founder can see the division of labor, not just
# the combined output.
AGENT_TASK_TH = {
    "lead_hunter": "หา Pain Point ของลูกค้า/ร้านจากข้อความนี้ เทียบกับ Pain Point 5 อันดับ",
    "sales_assistant": "ร่างข้อความเปิดคุย Messenger กับลีดที่มีสัญญาณสนใจ ไม่ขายตรง",
    "demo_agent": "เตรียมคำตอบเรื่องฟีเจอร์/แพ็กเกจให้ Founder ใช้ตอบลูกค้าที่กำลังพิจารณา",
    "onboarding_agent": "หาจุดที่ร้านใหม่ติดขัดระหว่างตั้งค่า/ยืนยันตัวตน/เริ่มใช้งานจริง",
    "customer_success_agent": "เช็กร้านที่ใช้งานอยู่ว่ามีการจองจริงหรือมีสัญญาณเสี่ยงเลิกใช้",
    "product_analyst_agent": "จัดกลุ่ม Feedback เป็นข้อเสนอ Roadmap ในขอบเขต Booking/Deposit/Schedule/Customer Flow เท่านั้น",
    "content_strategist": "วางแผนหากลุ่มเป้าหมายและคอนเทนต์บน Facebook + TikTok step-by-step — สอดส่องกลุ่ม/แฮชแท็กไหน คำพูดยังไง รูปแบบไหน DM ยังไง เสนอขายตอนไหน ปิดการขายยังไง",
}
