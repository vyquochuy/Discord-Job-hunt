import { useState, type ReactNode } from "react"

type Concept = "enterprise" | "glass" | "ai"
type Screen = "dashboard" | "jobs" | "matching" | "profile" | "applications" | "market" | "settings"

const conceptMeta: Record<Concept, {
  label: string
  short: string
  description: string
}> = {
  enterprise: {
    label: "Modern Enterprise",
    short: "A",
    description: "",
  },
  glass: { 
    label: "Liquid Glass", 
    short: "B", 
    description: "" },
  ai: {
    label: "AI Intelligence",
    short: "C",
    description: "",
  },
}

const navGroups: {
  label: string
  items: { id: Screen; label: string; icon: IconName }[]
}[] = [
  {
    label: "CANDIDATE INTELLIGENCE",
    items: [
      { id: "dashboard", label: "Tổng quan", icon: "grid" },
      { id: "jobs", label: "Khám phá việc làm", icon: "search" },
      { id: "matching", label: "AI Job Matching", icon: "spark" },
      { id: "profile", label: "Hồ sơ ứng viên", icon: "user" },
      { id: "applications", label: "Đơn ứng tuyển", icon: "briefcase" },
    ],
  },
  {
    label: "MARKET INTELLIGENCE",
    items: [
      { id: "market", label: "Phân tích thị trường", icon: "chart" },
      { id: "settings", label: "Cài đặt & quản trị", icon: "settings" },
    ],
  },
]

const pageTitles: Record<Screen, [string, string]> = {
  dashboard: [
    "Chào buổi sáng, Minh",
    "Mọi tín hiệu nghề nghiệp quan trọng, trong một không gian.",
  ],
  jobs: [
    "Khám phá việc làm",
    "Cơ hội phù hợp nhất được AI tuyển chọn riêng cho bạn.",
  ],
  matching: [
    "AI Job Matching",
    "Phân tích mức độ tương thích hồ sơ và yêu cầu tuyển dụng.",
  ],
  profile: [
    "Hồ sơ ứng viên",
    "Hồ sơ càng đầy đủ, đề xuất việc làm càng chính xác.",
  ],
  applications: [
    "Quản lý ứng tuyển",
    "Theo dõi toàn bộ hành trình tìm việc tại một nơi.",
  ],
  market: [
    "Thị trường IT Việt Nam",
    "Dữ liệu tuyển dụng được cập nhật đến 24/06/2025.",
  ],
  settings: [
    "Cài đặt & quản trị",
    "Quản lý tài khoản, nguồn dữ liệu và chất lượng hệ thống.",
  ],
}

type IconName = "grid" | "search" | "spark" | "user" | "briefcase" | "chart" | "settings" | "bell" | "chevron" | "arrow" | "bookmark" | "location" | "clock" | "check" | "plus" | "more" | "filter" | "upload" | "calendar" | "database" | "shield" | "activity" | "sun" | "command" | "building" | "graduation"

function Icon({
  name,
  size = 18,
  stroke = 1.8,
}: {
  name: IconName
  size?: number
  stroke?: number
}) {
  const paths: Partial<Record<IconName, ReactNode>> = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="2" />
        <rect x="14" y="3" width="7" height="7" rx="2" />
        <rect x="3" y="14" width="7" height="7" rx="2" />
        <rect x="14" y="14" width="7" height="7" rx="2" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    spark: (
      <>
        <path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3Z" />
        <path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
      </>
    ),
    briefcase: (
      <>
        <rect x="3" y="7" width="18" height="13" rx="3" />
        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2" />
      </>
    ),
    chart: (
      <>
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21h-4v-.08A1.7 1.7 0 0 0 8.94 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15 1.7 1.7 0 0 0 3.08 14H3v-4h.08A1.7 1.7 0 0 0 4.6 8.94a1.7 1.7 0 0 0-.34-1.88L4.2 7 7 4.2l.06.06A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3.08V3h4v.08A1.7 1.7 0 0 0 15.06 4.6a1.7 1.7 0 0 0 1.88-.34L17 4.2 19.8 7l-.06.06A1.7 1.7 0 0 0 19.4 9c.25.6.84 1 1.52 1H21v4h-.08c-.68 0-1.27.4-1.52 1Z" />
      </>
    ),
    bell: (
      <>
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
      </>
    ),
    chevron: <path d="m9 18 6-6-6-6" />,
    arrow: (
      <>
        <path d="M5 12h14M13 6l6 6-6 6" />
      </>
    ),
    bookmark: <path d="M6 3h12v18l-6-4-6 4V3Z" />,
    location: (
      <>
        <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" />
        <circle cx="12" cy="10" r="2.5" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    plus: (
      <>
        <path d="M12 5v14M5 12h14" />
      </>
    ),
    more: (
      <>
        <circle cx="5" cy="12" r="1" />
        <circle cx="12" cy="12" r="1" />
        <circle cx="19" cy="12" r="1" />
      </>
    ),
    filter: <path d="M4 5h16l-6 7v6l-4 2v-8L4 5Z" />,
    upload: (
      <>
        <path d="M12 16V4M7 9l5-5 5 5" />
        <path d="M4 15v5h16v-5" />
      </>
    ),
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="3" />
        <path d="M8 3v4M16 3v4M3 10h18" />
      </>
    ),
    database: (
      <>
        <ellipse cx="12" cy="5" rx="8" ry="3" />
        <path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7" />
      </>
    ),
    shield: (
      <path d="M12 3 4 6v5c0 5.2 3.4 8.5 8 10 4.6-1.5 8-4.8 8-10V6l-8-3Z" />
    ),
    activity: <path d="M3 12h4l2.5-7 5 14 2.5-7h4" />,
    sun: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </>
    ),
    command: (
      <>
        <path d="M9 6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6Z" />
      </>
    ),
    building: (
      <>
        <path d="M4 21V5l8-3 8 3v16M8 9h2M14 9h2M8 13h2M14 13h2M9 21v-4h6v4" />
      </>
    ),
    graduation: (
      <>
        <path d="m2 9 10-5 10 5-10 5L2 9Z" />
        <path d="M6 11v5c3 3 9 3 12 0v-5M22 9v6" />
      </>
    ),
  }
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {paths[name]}
    </svg>
  )
}

function Logo() {
  return (
    <div className="brand">
      <div className="brand-mark">
        <span>J</span>
      </div>
      <div>
        <strong>JOB HUNTER</strong>
        <small>AI Career Intelligence</small>
      </div>
    </div>
  )
}

function App() {
  const [concept, setConcept] = useState<Concept>("enterprise")
  const [screen, setScreen] = useState<Screen>("dashboard")
  const [mobileNav, setMobileNav] = useState(false)

  return (
    <div className={`app concept-${concept}`}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
        <Logo />
        <nav>
          {navGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <div className="nav-label">{group.label}</div>
              {group.items.map((item) => (
                <button
                  className={`nav-item ${screen === item.id ? "active" : ""}`}
                  onClick={() => {
                    setScreen(item.id)
                    setMobileNav(false)
                  }}
                  key={item.id}
                >
                  <span className="nav-icon">
                    <Icon name={item.icon} />
                  </span>
                  <span>{item.label}</span>
                  {screen === item.id && <span className="active-dot" />}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="help-card">
            <span className="help-spark">
              <Icon name="spark" size={16} />
            </span>
            <div>
              <strong>AI Career Coach</strong>
              <small>Nhận lời khuyên tức thì</small>
            </div>
            <Icon name="chevron" size={15} />
          </div>
          <div className="user-mini">
            <div className="avatar">MN</div>
            <div>
              <strong>Minh Nguyễn</strong>
              <small>Product Designer</small>
            </div>
            <Icon name="more" size={17} />
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileNav((v) => !v)}
          >
            <Icon name="grid" />
          </button>
          <div className="concept-switcher">
            {(Object.keys(conceptMeta) as Concept[]).map((key) => (
              <button
                key={key}
                onClick={() => setConcept(key)}
                className={concept === key ? "selected" : ""}
              >
                <b>{conceptMeta[key].short}</b>
                <span>{conceptMeta[key].label}</span>
              </button>
            ))}
          </div>
          <div className="top-actions">
            <div className="quick-search">
              <Icon name="search" size={16} />
              <span>Tìm kiếm nhanh</span>
              <kbd>⌘ K</kbd>
            </div>
            <button className="icon-button">
              <Icon name="bell" size={18} />
              <i />
            </button>
            <button className="avatar-button">MN</button>
          </div>
        </header>
        <section className="content">
          <PageHeader concept={concept} screen={screen} />
          {screen === "dashboard" && <Dashboard setScreen={setScreen} />}
          {screen === "jobs" && <Jobs />}
          {screen === "matching" && <Matching />}
          {screen === "profile" && <Profile />}
          {screen === "applications" && <Applications />}
          {screen === "market" && <Market />}
          {screen === "settings" && <Settings />}
        </section>
      </main>
    </div>
  )
}

function PageHeader({ concept, screen }: { concept: Concept; screen: Screen }) {
  return (
    <div className="page-header">
      <div>
        <div className="eyebrow">
          {conceptMeta[concept].short} / {conceptMeta[concept].label}{" "}
          <span>•</span> {conceptMeta[concept].description}
        </div>
        <h1>{pageTitles[screen][0]}</h1>
        <p>{pageTitles[screen][1]}</p>
      </div>
      <div className="header-actions">
        {screen === "market" && (
          <button className="button secondary">
            <Icon name="calendar" size={16} /> 30 ngày qua
          </button>
        )}
        <button className="button primary">
          <Icon name="spark" size={16} />
          {screen === "jobs"
            ? "Phân tích CV"
            : screen === "profile"
              ? "Tải CV mới"
              : "Hỏi AI Coach"}
        </button>
      </div>
    </div>
  )
}

const stats = [
  {
    label: "Việc làm đã theo dõi",
    value: "24",
    delta: "+6 tuần này",
    icon: "briefcase" as IconName,
  },
  {
    label: "Vị trí được đề xuất",
    value: "18",
    delta: "92% phù hợp nhất",
    icon: "spark" as IconName,
  },
  {
    label: "Việc làm đã lưu",
    value: "12",
    delta: "3 sắp hết hạn",
    icon: "bookmark" as IconName,
  },
  {
    label: "Đã ứng tuyển",
    value: "08",
    delta: "2 lịch phỏng vấn",
    icon: "arrow" as IconName,
  },
]

function Dashboard({ setScreen }: { setScreen: (s: Screen) => void }) {
  return (
    <div className="page-grid">
      <div className="stat-grid">
        {stats.map((s, i) => (
          <div className="card stat-card" key={s.label}>
            <div className={`stat-icon tone-${i}`}>
              <Icon name={s.icon} />
            </div>
            <div className="stat-copy">
              <span>{s.label}</span>
              <strong>{s.value}</strong>
              <small>{s.delta}</small>
            </div>
            <MiniSpark index={i} />
          </div>
        ))}
      </div>
      <div className="dash-main">
        <div className="card recommendations">
          <CardTitle
            title="Gợi ý phù hợp nhất"
            sub="Dựa trên hồ sơ và mục tiêu nghề nghiệp"
            action="Xem tất cả"
            onClick={() => setScreen("jobs")}
          />
          <div className="job-rows">
            <JobRow
              logo="F"
              color="#146EF5"
              company="FPT Software"
              role="Senior Product Designer"
              match={94}
              meta="Hà Nội · Hybrid"
              salary="35–50 triệu"
            />
            <JobRow
              logo="V"
              color="#E5484D"
              company="VNG Corporation"
              role="UX/UI Lead"
              match={91}
              meta="TP. Hồ Chí Minh · On-site"
              salary="40–55 triệu"
            />
            <JobRow
              logo="M"
              color="#111827"
              company="MoMo"
              role="Product Designer"
              match={88}
              meta="TP. Hồ Chí Minh · Hybrid"
              salary="30–45 triệu"
            />
          </div>
        </div>
        <div className="card ai-insight">
          <div className="ai-orb">
            <Icon name="spark" size={22} />
            <span />
            <span />
          </div>
          <div className="insight-tag">AI CAREER INSIGHT</div>
          <h3>
            Hồ sơ của bạn đang nổi bật hơn <em>78%</em> ứng viên cùng ngành.
          </h3>
          <p>
            Bổ sung kỹ năng <strong>Design Systems</strong> có thể tăng mức độ
            phù hợp thêm 12%.
          </p>
          <button className="text-action">
            Xem phân tích chi tiết <Icon name="arrow" size={15} />
          </button>
        </div>
      </div>
      <div className="dash-bottom">
        <div className="card activity-card">
          <CardTitle title="Hoạt động gần đây" sub="7 ngày qua" />
          <div className="timeline">
            <Activity
              icon="check"
              title="CV đã được phân tích"
              text="Điểm hồ sơ tăng từ 76 lên 84"
              time="12 phút trước"
            />
            <Activity
              icon="bookmark"
              title="Đã lưu một việc làm"
              text="Senior Product Designer · FPT Software"
              time="Hôm qua"
            />
            <Activity
              icon="calendar"
              title="Lịch phỏng vấn mới"
              text="UX Designer · Tiki, 09:30 Thứ Năm"
              time="2 ngày trước"
            />
          </div>
        </div>
        <div className="card progress-card">
          <CardTitle title="Tiến độ hồ sơ" sub="Sẵn sàng ứng tuyển" />
          <Donut value={84} />
          <div className="progress-list">
            <span>
              <i className="good" /> Thông tin cá nhân <b>100%</b>
            </span>
            <span>
              <i /> Kinh nghiệm làm việc <b>85%</b>
            </span>
            <span>
              <i /> Dự án nổi bật <b>70%</b>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

function Jobs() {
  const [selected, setSelected] = useState(0)
  const jobs = [
    [
      "F",
      "#146EF5",
      "Senior Product Designer",
      "FPT Software",
      "Hà Nội · Hybrid",
      "35–50 triệu",
      "94",
    ],
    [
      "V",
      "#E5484D",
      "UX/UI Lead",
      "VNG Corporation",
      "TP. Hồ Chí Minh · On-site",
      "40–55 triệu",
      "91",
    ],
    [
      "M",
      "#111827",
      "Product Designer",
      "MoMo",
      "TP. Hồ Chí Minh · Hybrid",
      "30–45 triệu",
      "88",
    ],
    [
      "T",
      "#F97316",
      "Senior UX Designer",
      "Tiki",
      "TP. Hồ Chí Minh · Remote",
      "32–48 triệu",
      "86",
    ],
  ]
  const job = jobs[selected]
  return (
    <div className="jobs-page">
      <div className="search-panel card">
        <div className="search-field">
          <Icon name="search" />
          <input aria-label="Tìm việc" defaultValue="Product Designer" />
          <span className="divider" />
          <Icon name="location" />
          <input aria-label="Địa điểm" defaultValue="Việt Nam" />
          <button className="button primary">Tìm việc</button>
        </div>
        <div className="filter-row">
          <button>
            <Icon name="filter" size={15} /> Bộ lọc
          </button>
          <button>
            Kinh nghiệm <Icon name="chevron" size={14} />
          </button>
          <button>
            Mức lương <Icon name="chevron" size={14} />
          </button>
          <button>
            Hình thức <Icon name="chevron" size={14} />
          </button>
          <button>
            Cấp bậc <Icon name="chevron" size={14} />
          </button>
          <span>18 việc làm phù hợp</span>
        </div>
      </div>
      <div className="jobs-layout">
        <div className="job-list card">
          <div className="list-heading">
            <strong>Việc làm dành cho bạn</strong>
            <button>
              Mới nhất <Icon name="chevron" size={13} />
            </button>
          </div>
          {jobs.map((j, i) => (
            <button
              className={`job-listing ${selected === i ? "selected" : ""}`}
              onClick={() => setSelected(i)}
              key={j[2]}
            >
              <CompanyLogo text={j[0]} color={j[1]} />
              <div className="listing-copy">
                <strong>{j[2]}</strong>
                <span>{j[3]}</span>
                <small>
                  <Icon name="location" size={13} /> {j[4]}
                </small>
                <small>{j[5]}</small>
              </div>
              <div className="listing-side">
                <MatchPill value={j[6]} />
                <Icon name="bookmark" size={17} />
                <small>{i + 1} giờ trước</small>
              </div>
            </button>
          ))}
        </div>
        <div className="job-detail card">
          <div className="detail-top">
            <CompanyLogo text={job[0]} color={job[1]} large />
            <div>
              <h2>{job[2]}</h2>
              <p>
                {job[3]} · {job[4]}
              </p>
            </div>
            <button className="icon-button">
              <Icon name="bookmark" />
            </button>
          </div>
          <div className="detail-meta">
            <div>
              <span>Mức lương</span>
              <strong>{job[5]}</strong>
            </div>
            <div>
              <span>Kinh nghiệm</span>
              <strong>3–5 năm</strong>
            </div>
            <div>
              <span>Hình thức</span>
              <strong>Toàn thời gian</strong>
            </div>
          </div>
          <div className="match-banner">
            <Donut value={Number(job[6])} small />
            <div>
              <strong>Rất phù hợp với bạn</strong>
              <span>12/14 kỹ năng tương thích với hồ sơ</span>
            </div>
            <button>
              Chi tiết <Icon name="arrow" size={14} />
            </button>
          </div>
          <h3>Mô tả công việc</h3>
          <p className="body-copy">
            Dẫn dắt quy trình thiết kế sản phẩm từ khám phá vấn đề đến bàn giao.
            Cộng tác cùng Product và Engineering để tạo ra trải nghiệm số đơn
            giản, hiệu quả.
          </p>
          <h3>Kỹ năng yêu cầu</h3>
          <div className="tags">
            <span>Figma</span>
            <span>Design System</span>
            <span>UX Research</span>
            <span>Prototyping</span>
          </div>
          <div className="detail-actions">
            <button className="button secondary">Lưu việc làm</button>
            <button className="button primary">
              Ứng tuyển ngay <Icon name="arrow" size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Matching() {
  return (
    <div className="match-page">
      <div className="card candidate-strip">
        <div className="avatar large">MN</div>
        <div>
          <span>ĐANG PHÂN TÍCH CHO</span>
          <h3>Minh Nguyễn</h3>
          <p>Senior Product Designer · 5 năm kinh nghiệm</p>
        </div>
        <div className="candidate-skills">
          <span>Figma</span>
          <span>UX Strategy</span>
          <span>Research</span>
          <span>+9</span>
        </div>
        <button className="button secondary">Đổi hồ sơ</button>
      </div>
      <div className="match-hero">
        <div className="card score-card">
          <div className="score-rings">
            <Donut value={92} />
            <span className="pulse-ring" />
          </div>
          <span className="score-label">ĐỘ TƯƠNG THÍCH TỔNG THỂ</span>
          <h2>Ứng viên nổi bật</h2>
          <p>Bạn thuộc top 8% ứng viên phù hợp nhất cho vị trí này.</p>
          <div className="score-company">
            <CompanyLogo text="F" color="#146EF5" />
            <div>
              <strong>Senior Product Designer</strong>
              <span>FPT Software</span>
            </div>
          </div>
        </div>
        <div className="card dimension-card">
          <CardTitle
            title="Phân tích tương thích"
            sub="So sánh hồ sơ với yêu cầu tuyển dụng"
          />
          <Compatibility label="Kỹ năng chuyên môn" value={94} color="blue" />
          <Compatibility label="Kinh nghiệm" value={90} color="violet" />
          <Compatibility label="Học vấn" value={86} color="cyan" />
          <Compatibility
            label="Địa điểm & hình thức"
            value={100}
            color="green"
          />
        </div>
        <div className="card match-skills">
          <CardTitle
            title="Đối chiếu kỹ năng"
            sub="12/14 kỹ năng tương thích"
          />
          <div className="skills-columns">
            <div>
              <span className="column-label good">ĐÃ ĐÁP ỨNG</span>
              {[
                "Figma",
                "Design Systems",
                "UX Research",
                "Prototyping",
                "Agile",
              ].map((s) => (
                <p key={s}>
                  <Icon name="check" size={14} />
                  {s}
                  <b>Khớp</b>
                </p>
              ))}
            </div>
            <div>
              <span className="column-label missing">CẦN CẢI THIỆN</span>
              <p>
                <i />
                Data Visualization<b>Ưu tiên</b>
              </p>
              <p>
                <i />
                B2B SaaS<b>Nên bổ sung</b>
              </p>
              <div className="suggestion">
                <Icon name="spark" size={16} />
                <span>
                  <strong>Gợi ý từ AI</strong>Hoàn thành khóa Data Visualization
                  cơ bản để tăng 6% điểm.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Profile() {
  return (
    <div className="profile-layout">
      <div className="card profile-identity">
        <div className="profile-cover" />
        <div className="avatar xlarge">MN</div>
        <h2>Minh Nguyễn</h2>
        <p>Senior Product Designer</p>
        <small>TP. Hồ Chí Minh · Sẵn sàng làm việc</small>
        <div className="profile-score">
          <Donut value={84} small />
          <span>
            <strong>84% hoàn thiện</strong>
            <small>Thêm dự án để nổi bật hơn</small>
          </span>
        </div>
        <button className="button primary full">Chỉnh sửa hồ sơ</button>
      </div>
      <div className="profile-sections">
        <div className="card profile-section">
          <CardTitle title="Giới thiệu chuyên môn" action="Chỉnh sửa" />
          <p>
            Product Designer với 5 năm kinh nghiệm xây dựng sản phẩm số cho
            fintech và thương mại điện tử. Tập trung vào trải nghiệm đơn giản,
            có thể đo lường.
          </p>
        </div>
        <div className="card profile-section">
          <CardTitle title="Kỹ năng chuyên môn" action="+ Thêm kỹ năng" />
          <div className="skill-cloud">
            {[
              "Figma · Chuyên gia",
              "Design Systems",
              "UX Research",
              "Prototyping",
              "Product Strategy",
              "Data Analysis",
            ].map((x) => (
              <span key={x}>{x}</span>
            ))}
          </div>
        </div>
        <div className="card profile-section">
          <CardTitle title="Kinh nghiệm làm việc" action="+ Thêm" />
          <Experience
            logo="M"
            color="#111827"
            role="Senior Product Designer"
            company="MoMo"
            date="01/2022 — Hiện tại"
          />
          <Experience
            logo="T"
            color="#f97316"
            role="Product Designer"
            company="Tiki"
            date="06/2019 — 12/2021"
          />
        </div>
      </div>
      <div className="profile-side">
        <div className="card resume-card">
          <CardTitle title="Hồ sơ CV" />
          <div className="resume-file">
            <Icon name="upload" />
            <div>
              <strong>Minh_Nguyen_CV_2025.pdf</strong>
              <small>Cập nhật 2 ngày trước · 1.8 MB</small>
            </div>
          </div>
          <button className="button secondary full">Thay CV</button>
        </div>
        <div className="card">
          <CardTitle title="Học vấn" />
          <Experience
            logo="R"
            color="#7c3aed"
            role="Thiết kế truyền thông"
            company="Đại học RMIT Việt Nam"
            date="2015 — 2019"
          />
        </div>
      </div>
    </div>
  )
}

function Applications() {
  const cols = [
    {
      title: "Đã lưu",
      count: 5,
      jobs: [
        ["FPT Software", "Senior Product Designer", "F", "#146EF5"],
        ["Tiki", "Senior UX Designer", "T", "#f97316"],
      ],
    },
    {
      title: "Đã ứng tuyển",
      count: 3,
      jobs: [
        ["VNG Corporation", "UX/UI Lead", "V", "#e5484d"],
        ["Grab Vietnam", "Product Designer", "G", "#16a34a"],
      ],
    },
    {
      title: "Phỏng vấn",
      count: 2,
      jobs: [
        ["MoMo", "Product Designer", "M", "#111827"],
        ["NashTech", "UX Lead", "N", "#2563eb"],
      ],
    },
    {
      title: "Đề nghị",
      count: 1,
      jobs: [["KMS Technology", "Design Lead", "K", "#7c3aed"]],
    },
  ]
  return (
    <div className="applications-page">
      <div className="application-stats">
        <div className="card">
          <span>Tổng đơn ứng tuyển</span>
          <strong>08</strong>
          <small>+3 tháng này</small>
        </div>
        <div className="card">
          <span>Tỷ lệ phản hồi</span>
          <strong>62%</strong>
          <small>Cao hơn 18% TB</small>
        </div>
        <div className="card">
          <span>Lịch phỏng vấn</span>
          <strong>02</strong>
          <small>Gần nhất: Thứ Năm</small>
        </div>
        <div className="card">
          <span>Đề nghị nhận việc</span>
          <strong>01</strong>
          <small>Hạn trả lời: 28/06</small>
        </div>
      </div>
      <div className="board-toolbar">
        <div>
          <button className="active">Pipeline</button>
          <button>Danh sách</button>
        </div>
        <button className="button primary">
          <Icon name="plus" size={16} /> Thêm ứng tuyển
        </button>
      </div>
      <div className="kanban">
        {cols.map((col, ci) => (
          <div className="kanban-col" key={col.title}>
            <div className="kanban-title">
              <span>
                <i className={`stage-${ci}`} />
                {col.title}
                <b>{col.count}</b>
              </span>
              <Icon name="more" size={17} />
            </div>
            {col.jobs.map((j, i) => (
              <div className="card kanban-card" key={j[1]}>
                <div>
                  <CompanyLogo text={j[2]} color={j[3]} />
                  <Icon name="more" size={16} />
                </div>
                <h3>{j[1]}</h3>
                <p>{j[0]}</p>
                <div className="kanban-meta">
                  <span>
                    <Icon name="calendar" size={13} />
                    {ci === 2 ? "PV 26/06" : `${i + 2} ngày trước`}
                  </span>
                  <span className={ci === 2 ? "priority" : ""}>
                    {ci === 2 ? "Sắp tới" : "Full-time"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function Market() {
  return (
    <div className="market-page">
      <div className="market-stats">
        <div className="card market-stat">
          <span>Tổng tin tuyển dụng</span>
          <strong>12,842</strong>
          <small className="up">↗ 12.4% so với tháng trước</small>
          <MiniSpark index={0} />
        </div>
        <div className="card market-stat">
          <span>Doanh nghiệp tuyển dụng</span>
          <strong>2,164</strong>
          <small className="up">↗ 8.7% tăng trưởng</small>
          <MiniSpark index={1} />
        </div>
        <div className="card market-stat">
          <span>Mức lương trung vị</span>
          <strong>
            32.5<em> triệu</em>
          </strong>
          <small className="up">↗ 5.2% so với quý trước</small>
          <MiniSpark index={2} />
        </div>
        <div className="card market-stat">
          <span>Nhu cầu nhân lực</span>
          <strong>High</strong>
          <small>Chỉ số thị trường: 78/100</small>
          <div className="market-gauge">
            <i />
          </div>
        </div>
      </div>
      <div className="market-middle">
        <div className="card hiring-chart">
          <CardTitle
            title="Xu hướng tuyển dụng"
            sub="Số tin tuyển dụng IT theo tháng"
            action="12 tháng"
          />
          <LineChart />
        </div>
        <div className="card tech-demand">
          <CardTitle
            title="Công nghệ được săn đón"
            sub="Theo số lượng tin tuyển dụng"
          />
          {[
            ["JavaScript", 86, "#4F7CFF"],
            ["Java", 73, "#8B5CF6"],
            ["Python", 68, "#0CC8D3"],
            ["React", 62, "#38BDF8"],
            [".NET", 54, "#A78BFA"],
          ].map(([n, v, c], i) => (
            <div className="rank" key={n as string}>
              <b>0{i + 1}</b>
              <span>{n}</span>
              <div>
                <i style={{ width: `${v}%`, background: c as string }} />
              </div>
              <strong>{v}%</strong>
            </div>
          ))}
        </div>
      </div>
      <div className="market-bottom">
        <div className="card">
          <CardTitle title="Phân bổ cấp bậc" sub="Theo tổng nhu cầu" />
          <div className="seniority">
            <Donut value={64} />
            <div>
              <span>
                <i style={{ background: "#4f7cff" }} />
                Fresher / Junior <b>24%</b>
              </span>
              <span>
                <i style={{ background: "#8b5cf6" }} />
                Middle <b>38%</b>
              </span>
              <span>
                <i style={{ background: "#0cc8d3" }} />
                Senior <b>28%</b>
              </span>
              <span>
                <i style={{ background: "#f5b942" }} />
                Lead / Manager <b>10%</b>
              </span>
            </div>
          </div>
        </div>
        <div className="card geography">
          <CardTitle title="Phân bổ theo địa lý" sub="Điểm nóng tuyển dụng" />
          <div className="geo-bars">
            <span>
              TP. Hồ Chí Minh <b>48%</b>
              <i>
                <em style={{ width: "88%" }} />
              </i>
            </span>
            <span>
              Hà Nội <b>36%</b>
              <i>
                <em style={{ width: "70%" }} />
              </i>
            </span>
            <span>
              Đà Nẵng <b>9%</b>
              <i>
                <em style={{ width: "25%" }} />
              </i>
            </span>
            <span>
              Khác <b>7%</b>
              <i>
                <em style={{ width: "18%" }} />
              </i>
            </span>
          </div>
        </div>
        <div className="card top-companies">
          <CardTitle title="Doanh nghiệp tuyển nhiều" action="Xem báo cáo" />
          <JobRow
            logo="F"
            color="#146EF5"
            company="FPT Software"
            role="324 vị trí đang mở"
            match={12}
            meta="↗ so với tháng trước"
            salary=""
          />
          <JobRow
            logo="V"
            color="#e5484d"
            company="VNG Corporation"
            role="186 vị trí đang mở"
            match={8}
            meta="↗ so với tháng trước"
            salary=""
          />
        </div>
      </div>
    </div>
  )
}

function Settings() {
  return (
    <div className="settings-page">
      <div className="settings-nav card">
        {[
          ["user", "Tài khoản"],
          ["settings", "Cấu hình hệ thống"],
          ["database", "Nguồn dữ liệu"],
          ["activity", "Trạng thái crawler"],
          ["shield", "Chất lượng dữ liệu"],
        ].map((x, i) => (
          <button className={i === 2 ? "active" : ""} key={x[1]}>
            <Icon name={x[0] as IconName} />
            {x[1]}
            <Icon name="chevron" size={14} />
          </button>
        ))}
      </div>
      <div className="settings-content">
        <div className="card settings-hero">
          <div>
            <span>DATA OPERATIONS</span>
            <h2>Quản lý nguồn dữ liệu</h2>
            <p>Theo dõi kết nối và đồng bộ từ các nền tảng tuyển dụng.</p>
          </div>
          <button className="button primary">
            <Icon name="plus" size={15} /> Thêm nguồn
          </button>
        </div>
        <div className="card source-table">
          <div className="table-head">
            <span>Nguồn dữ liệu</span>
            <span>Trạng thái</span>
            <span>Lần đồng bộ cuối</span>
            <span>Bản ghi</span>
            <span />
          </div>
          {[
            ["TopCV", "Đang hoạt động", "4 phút trước", "4,281"],
            ["VietnamWorks", "Đang hoạt động", "12 phút trước", "3,496"],
            ["LinkedIn Jobs", "Đang hoạt động", "18 phút trước", "2,814"],
            ["ITviec", "Tạm dừng", "2 giờ trước", "2,251"],
          ].map((r, i) => (
            <div className="table-row" key={r[0]}>
              <span>
                <i className={`source-logo s${i}`}>{r[0][0]}</i>
                <b>{r[0]}</b>
              </span>
              <span className={i === 3 ? "paused" : "live"}>
                <i />
                {r[1]}
              </span>
              <span>{r[2]}</span>
              <span>{r[3]}</span>
              <button>
                <Icon name="more" size={17} />
              </button>
            </div>
          ))}
        </div>
        <div className="settings-cards">
          <div className="card quality">
            <CardTitle
              title="Chất lượng dữ liệu"
              sub="Điểm tổng hợp 24 giờ qua"
            />
            <strong>96.8%</strong>
            <div className="quality-bar">
              <i />
            </div>
            <span>
              Độ đầy đủ <b>98%</b>
            </span>
            <span>
              Độ chính xác <b>97%</b>
            </span>
            <span>
              Độ mới <b>94%</b>
            </span>
          </div>
          <div className="card crawler">
            <CardTitle title="Crawler status" action="Xem logs" />
            <div className="crawler-online">
              <i />
              <span>
                <strong>Hệ thống hoạt động ổn định</strong>
                <small>12 workers đang chạy</small>
              </span>
            </div>
            <div className="crawler-stats">
              <span>
                <b>42.8K</b>Trang / giờ
              </span>
              <span>
                <b>0.2%</b>Tỷ lệ lỗi
              </span>
              <span>
                <b>38 ms</b>Độ trễ TB
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function CardTitle({
  title,
  sub,
  action,
  onClick,
}: {
  title: string
  sub?: string
  action?: string
  onClick?: () => void
}) {
  return (
    <div className="card-title">
      <div>
        <h2>{title}</h2>
        {sub && <p>{sub}</p>}
      </div>
      {action && (
        <button onClick={onClick}>
          {action}
          <Icon name="chevron" size={14} />
        </button>
      )}
    </div>
  )
}
function CompanyLogo({
  text,
  color,
  large,
}: {
  text: string
  color: string
  large?: boolean
}) {
  return (
    <span
      className={`company-logo ${large ? "large" : ""}`}
      style={{ background: color }}
    >
      {text}
    </span>
  )
}
function MatchPill({ value }: { value: string }) {
  return (
    <span className="match-pill">
      <Icon name="spark" size={12} />
      {value}%
    </span>
  )
}
function JobRow({
  logo,
  color,
  company,
  role,
  match,
  meta,
  salary,
}: {
  logo: string
  color: string
  company: string
  role: string
  match: number
  meta: string
  salary: string
}) {
  return (
    <div className="job-row">
      <CompanyLogo text={logo} color={color} />
      <div>
        <strong>{role}</strong>
        <span>{company}</span>
      </div>
      <div className="job-meta">
        <span>{meta}</span>
        {salary && <b>{salary}</b>}
      </div>
      <MatchPill value={String(match)} />
      <button>
        <Icon name="chevron" size={16} />
      </button>
    </div>
  )
}
function Activity({
  icon,
  title,
  text,
  time,
}: {
  icon: IconName
  title: string
  text: string
  time: string
}) {
  return (
    <div className="activity">
      <span>
        <Icon name={icon} size={15} />
      </span>
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
      <time>{time}</time>
    </div>
  )
}
function Compatibility({
  label,
  value,
  color,
}: {
  label: string
  value: number
  color: string
}) {
  return (
    <div className="compat">
      <div>
        <span>{label}</span>
        <strong>{value}%</strong>
      </div>
      <i>
        <em className={color} style={{ width: `${value}%` }} />
      </i>
    </div>
  )
}
function Experience({
  logo,
  color,
  role,
  company,
  date,
}: {
  logo: string
  color: string
  role: string
  company: string
  date: string
}) {
  return (
    <div className="experience">
      <CompanyLogo text={logo} color={color} />
      <div>
        <strong>{role}</strong>
        <span>{company}</span>
        <small>{date}</small>
      </div>
      <button>
        <Icon name="more" size={16} />
      </button>
    </div>
  )
}
function MiniSpark({ index }: { index: number }) {
  const colors = ["#4f7cff", "#8b5cf6", "#0cc8d3", "#f5b942"]
  return (
    <svg className="mini-spark" viewBox="0 0 90 38" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`sg${index}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={colors[index]} stopOpacity=".28" />
          <stop offset="1" stopColor={colors[index]} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d={
          index % 2
            ? "M1 30 C12 28 18 15 29 22 S44 30 54 16 70 12 89 4"
            : "M1 31 C14 35 17 19 30 23 S45 28 57 15 71 16 89 5"
        }
        fill="none"
        stroke={colors[index]}
        strokeWidth="2"
      />
      <path
        d={`${
          index % 2
            ? "M1 30 C12 28 18 15 29 22 S44 30 54 16 70 12 89 4"
            : "M1 31 C14 35 17 19 30 23 S45 28 57 15 71 16 89 5"
        } L89 38 L1 38Z`}
        fill={`url(#sg${index})`}
      />
    </svg>
  )
}
function Donut({ value, small }: { value: number; small?: boolean }) {
  return (
    <div
      className={`donut ${small ? "small" : ""}`}
      style={{ "--value": `${value * 3.6}deg` } as React.CSSProperties}
    >
      <div>
        <strong>{value}</strong>
        <span>%</span>
      </div>
    </div>
  )
}
function LineChart() {
  return (
    <div className="line-chart">
      <div className="y-labels">
        <span>4K</span>
        <span>3K</span>
        <span>2K</span>
        <span>1K</span>
      </div>
      <svg viewBox="0 0 700 190" preserveAspectRatio="none">
        <defs>
          <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#4f7cff" stopOpacity=".28" />
            <stop offset="1" stopColor="#4f7cff" stopOpacity="0" />
          </linearGradient>
        </defs>
        <g className="grid-lines">
          <path d="M0 20H700M0 70H700M0 120H700M0 170H700" />
        </g>
        <path
          className="area"
          d="M0 142 C40 137 58 119 95 126 S150 147 190 112 245 94 285 101 340 74 380 82 440 102 475 62 530 44 570 53 625 28 700 22V190H0Z"
        />
        <path
          className="line"
          d="M0 142 C40 137 58 119 95 126 S150 147 190 112 245 94 285 101 340 74 380 82 440 102 475 62 530 44 570 53 625 28 700 22"
        />
        <g className="points">
          {[
            [95, 126],
            [190, 112],
            [285, 101],
            [380, 82],
            [475, 62],
            [570, 53],
            [700, 22],
          ].map(([x, y]) => (
            <circle key={x} cx={x} cy={y} r="4" />
          ))}
        </g>
      </svg>
      <div className="x-labels">
        {[
          "T7",
          "T8",
          "T9",
          "T10",
          "T11",
          "T12",
          "T1",
          "T2",
          "T3",
          "T4",
          "T5",
          "T6",
        ].map((x) => (
          <span key={x}>{x}</span>
        ))}
      </div>
    </div>
  )
}

export default App
