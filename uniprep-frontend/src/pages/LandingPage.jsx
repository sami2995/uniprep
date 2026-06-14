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
                <ProofItem value="PDF" label="study material upload" />
                <ProofItem value="AI" label="summaries and quizzes" />
                <ProofItem value="100%" label="readiness tracking" />
              </div>
            </div>

            <div className="col-lg-6">
              <div className="exam-command-center">
                <div className="command-header">
                  <div>
                    <p className="command-eyebrow mb-1">Readiness snapshot</p>
                    <h2 className="mb-0">BSc Exit Exam Readiness</h2>
                  </div>

                  <span className="live-pill">Live</span>
                </div>

                <div className="readiness-panel">
                  <div>
                    <span className="panel-label">Overall readiness</span>
                    <strong>76%</strong>
                    <p>Up 9% after three focused mock exams</p>
                  </div>

                  <div className="readiness-ring">
                    <span>76</span>
                  </div>
                </div>

                <div className="domain-bars">
                  <DomainBar label="Data Structures" value={82} tone="blue" />
                  <DomainBar label="Operating Systems" value={68} tone="green" />
                  <DomainBar label="Computer Networks" value={54} tone="amber" />
                  <DomainBar label="Database Systems" value={73} tone="blue" />
                </div>

                <div className="next-action">
                  <Brain size={20} />
                  <div>
                    <strong>Next best move</strong>
                    <p>
                      Review subnetting and deadlocks, then take a 25-question
                      adaptive mock exam.
                    </p>
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
            <h2>One platform for studying, testing, and improving.</h2>
            <p>
              UniPrep connects personal study material with official-style exam
              practice, so preparation feels organized instead of scattered.
            </p>
          </div>

          <div className="row g-4">
            <LandingFeature
              icon={UploadCloud}
              title="Upload your study PDFs"
              text="Turn lecture notes and modules into searchable chunks, summaries, flashcards, and quizzes."
            />
            <LandingFeature
              icon={BookOpenCheck}
              title="Practice like the real exam"
              text="Take timed mock exams from an admin-reviewed question bank mapped by course, domain, and topic."
            />
            <LandingFeature
              icon={Gauge}
              title="Know your readiness"
              text="See weak topics, topic accuracy, recent performance, focus time, and readiness by course."
            />
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
                Students do not just answer questions. They build a weekly study
                rhythm, measure improvement, and get targeted AI support from
                their own materials.
              </p>
            </div>

            <div className="col-lg-7">
              <div className="student-flow">
                <FlowStep
                  icon={LibraryBig}
                  title="Build a study library"
                  text="Upload PDFs, classify by course or topic, and process them for AI study."
                />
                <FlowStep
                  icon={Sparkles}
                  title="Generate study assets"
                  text="Create summaries, flashcards, and quiz questions from uploaded material."
                />
                <FlowStep
                  icon={Clock3}
                  title="Practice under pressure"
                  text="Use timed mock exams and Pomodoro focus tracking to simulate real preparation."
                />
                <FlowStep
                  icon={BarChart3}
                  title="Review what matters"
                  text="Use analytics to revisit weak domains and grow readiness over time."
                />
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
                <AdminCapability
                  icon={FileSearch}
                  title="PDF import pipeline"
                  text="Extract questions from mock and past exam documents."
                />
                <AdminCapability
                  icon={ShieldCheck}
                  title="Approval workflow"
                  text="Keep draft, rejected, and approved questions separate."
                />
                <AdminCapability
                  icon={GraduationCap}
                  title="Course taxonomy"
                  text="Manage courses, domains, topics, and weights."
                />
                <AdminCapability
                  icon={CheckCircle2}
                  title="Blueprint rules"
                  text="Generate exams with controlled domain distribution."
                />
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
    <div className="domain-track">
      <div className={`domain-fill ${tone}`} style={{ width: `${value}%` }} />
    </div>
  </div>
);

const LandingFeature = ({ icon: Icon, title, text }) => (
  <div className="col-md-4">
    <article className="landing-feature h-100">
      <div className="landing-feature-icon">
        <Icon size={24} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  </div>
);

const FlowStep = ({ icon: Icon, title, text }) => (
  <article className="flow-step">
    <div className="flow-icon">
      <Icon size={22} />
    </div>
    <div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  </article>
);

const AdminCapability = ({ icon: Icon, title, text }) => (
  <article className="admin-capability">
    <Icon size={24} />
    <h3>{title}</h3>
    <p>{text}</p>
  </article>
);

export default LandingPage;
