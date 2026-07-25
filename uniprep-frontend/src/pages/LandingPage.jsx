import { Link } from "react-router-dom";
import {
  BarChart3,
  BookOpenCheck,
  Brain,
  CheckCircle2,
  Clock3,
  FileSearch,
  Gauge,
  GraduationCap,
  LibraryBig,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import heroImage from "../assets/hero.png";

// ---- Content, separated from markup so it's easy to update or wire to real data ----

const readiness = {
  overall: 76,
  trend: "Up 9% after three focused mock exams",
  domains: [
    { label: "Data Structures", value: 82, tone: "blue" },
    { label: "Operating Systems", value: 68, tone: "green" },
    { label: "Computer Networks", value: 54, tone: "amber" },
    { label: "Database Systems", value: 73, tone: "blue" },
  ],
  nextMove: "Review subnetting and deadlocks, then take a 25-question adaptive mock exam.",
};

const studentFeatures = [
  {
    icon: UploadCloud,
    title: "Upload your study PDFs",
    text: "Turn lecture notes and modules into searchable chunks, summaries, flashcards, and quizzes.",
  },
  {
    icon: BookOpenCheck,
    title: "Practice like the real exam",
    text: "Take timed mock exams from an admin-reviewed question bank mapped by course, domain, and topic.",
  },
  {
    icon: Gauge,
    title: "Know your readiness",
    text: "See weak topics, topic accuracy, recent performance, focus time, and readiness by course.",
  },
];

const studentFlow = [
  {
    icon: LibraryBig,
    title: "Build a study library",
    text: "Upload PDFs, classify by course or topic, and process them for AI study.",
  },
  {
    icon: Sparkles,
    title: "Generate study assets",
    text: "Create summaries, flashcards, and quiz questions from uploaded material.",
  },
  {
    icon: Clock3,
    title: "Practice under pressure",
    text: "Use timed mock exams and Pomodoro focus tracking to simulate real preparation.",
  },
  {
    icon: BarChart3,
    title: "Review what matters",
    text: "Use analytics to revisit weak domains and grow readiness over time.",
  },
];

const adminCapabilities = [
  {
    icon: FileSearch,
    title: "PDF import pipeline",
    text: "Extract questions from mock and past exam documents.",
  },
  {
    icon: ShieldCheck,
    title: "Approval workflow",
    text: "Keep draft, rejected, and approved questions separate.",
  },
  {
    icon: GraduationCap,
    title: "Course taxonomy",
    text: "Manage courses, domains, topics, and weights.",
  },
  {
    icon: CheckCircle2,
    title: "Blueprint rules",
    text: "Generate exams with controlled domain distribution.",
  },
];

const proof = [
  { value: "PDF", label: "study material upload" },
  { value: "AI", label: "summaries and quizzes" },
  { value: "100%", label: "readiness tracking" },
];

const LandingPage = () => {
  return (
    <main className="landing-page pro-landing">
      <section className="landing-hero">
        <div className="landing-hero-media" aria-hidden="true">
          <img src={heroImage} alt="" />
        </div>

        <div className="container position-relative">
          <div className="row align-items-center g-5 landing-hero-grid">
            <div className="col-lg-6">
              <span className="landing-kicker">
                Built for Ethiopian BSc Exit Exam preparation
              </span>

              <h1 className="landing-title mt-3">UniPrep AI</h1>

              <p className="landing-lede mt-3">
                A focused preparation platform where students turn PDFs into
                study tools, take adaptive mock exams, and understand their
                readiness before the national Exit Exam.
              </p>

              <div className="landing-actions mt-4">
                <Link to="/register" className="btn btn-light btn-lg px-4">
                  Start Preparing
                </Link>

                <Link to="/login" className="btn btn-outline-light btn-lg px-4">
                  Sign In
                </Link>
              </div>

              <div className="landing-proof">
                {proof.map((item) => (
                  <ProofItem key={item.value} {...item} />
                ))}
              </div>
            </div>

            <div className="col-lg-6">
              <div className="exam-command-center" aria-label="Sample readiness dashboard">
                <div className="command-header">
                  <div>
                    <p className="command-eyebrow mb-1">Readiness snapshot</p>
                    <h2 className="mb-0">BSc Exit Exam Readiness</h2>
                  </div>

                  <span className="live-pill">
                    <span className="visually-hidden">Status: </span>Live
                  </span>
                </div>

                <div className="readiness-panel">
                  <div>
                    <span className="panel-label">Overall readiness</span>
                    <strong>{readiness.overall}%</strong>
                    <p>{readiness.trend}</p>
                  </div>

                  <div
                    className="readiness-ring"
                    role="img"
                    aria-label={`Overall readiness ${readiness.overall} percent`}
                  >
                    <span aria-hidden="true">{readiness.overall}</span>
                  </div>
                </div>

                <div className="domain-bars">
                  {readiness.domains.map((domain) => (
                    <DomainBar key={domain.label} {...domain} />
                  ))}
                </div>

                <div className="next-action">
                  <Brain size={20} aria-hidden="true" />
                  <div>
                    <strong>Next best move</strong>
                    <p>{readiness.nextMove}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="container">
          <div className="section-heading">
            <span className="landing-kicker light">What makes it different</span>
            <h2>Study material and exam practice, in one loop.</h2>
            <p>
              UniPrep connects your own notes with official-style exam
              practice, so every study session points back to a measurable
              readiness score.
            </p>
          </div>

          <div className="row g-4">
            {studentFeatures.map((feature) => (
              <LandingFeature key={feature.title} {...feature} />
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section exam-flow-section">
        <div className="container">
          <div className="row align-items-center g-5">
            <div className="col-lg-5">
              <span className="landing-kicker light">For students</span>
              <h2 className="flow-title">A calm path from notes to exam confidence.</h2>
              <p className="flow-copy">
                Students do not just answer questions. They build a weekly
                study rhythm, measure improvement, and get targeted AI support
                from their own materials.
              </p>
            </div>

            <div className="col-lg-7">
              <div className="student-flow">
                {studentFlow.map((step) => (
                  <FlowStep key={step.title} {...step} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section admin-section">
        <div className="container">
          <div className="row g-4 align-items-stretch">
            <div className="col-lg-5">
              <div className="admin-copy">
                <span className="landing-kicker light">For admins</span>
                <h2>Control the official exam bank with review built in.</h2>
                <p>
                  Admins can import past exam PDFs, review extracted MCQs,
                  approve only verified questions, and shape mock exams with
                  blueprint rules.
                </p>
              </div>
            </div>

            <div className="col-lg-7">
              <div className="admin-grid">
                {adminCapabilities.map((capability) => (
                  <AdminCapability key={capability.title} {...capability} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-cta">
        <div className="container">
          <div className="cta-inner">
            <div>
              <span className="landing-kicker light">Ready when you are</span>
              <h2>Prepare with structure, evidence, and AI support.</h2>
              <p>
                Start with your materials, take a mock exam, and let UniPrep
                show you exactly what needs attention next.
              </p>
            </div>

            <div className="cta-actions">
              <Link to="/register" className="btn btn-primary btn-lg px-4">
                Create Account
              </Link>
              <Link to="/login" className="btn btn-outline-dark btn-lg px-4">
                Login
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
};

const ProofItem = ({ value, label }) => (
  <div>
    <strong>{value}</strong>
    <span>{label}</span>
  </div>
);

const DomainBar = ({ label, value, tone }) => (
  <div className="domain-bar">
    <div className="domain-bar-top">
      <span>{label}</span>
      <strong>{value}%</strong>
    </div>
    <div
      className="domain-track"
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`${label} readiness`}
    >
      <div className={`domain-fill ${tone}`} style={{ width: `${value}%` }} />
    </div>
  </div>
);

const LandingFeature = ({ icon: Icon, title, text }) => (
  <div className="col-md-4">
    <article className="landing-feature h-100">
      <div className="landing-feature-icon">
        <Icon size={24} aria-hidden="true" />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  </div>
);

const FlowStep = ({ icon: Icon, title, text }) => (
  <article className="flow-step">
    <div className="flow-icon">
      <Icon size={22} aria-hidden="true" />
    </div>
    <div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  </article>
);

const AdminCapability = ({ icon: Icon, title, text }) => (
  <article className="admin-capability">
    <Icon size={24} aria-hidden="true" />
    <h3>{title}</h3>
    <p>{text}</p>
  </article>
);

export default LandingPage;