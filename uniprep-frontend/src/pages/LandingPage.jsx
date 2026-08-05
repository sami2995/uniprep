import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowDown,
  ArrowRight,
  Gauge,
  LibraryBig,
  ShieldCheck,
  Target,
} from "lucide-react";

// ---- Content, separated from markup so it's easy to update or wire to real data ----

const features = [
  {
    icon: LibraryBig,
    title: "Grounded study space",
    text: "Upload your own lecture PDFs and study with AI summaries, chat, flashcards, and quizzes generated from your materials — not generic content.",
  },
  {
    icon: ShieldCheck,
    title: "Department-approved questions",
    text: "Every question passes a departmental review and approval workflow, so the bank you practice from is governed by your department.",
  },
  {
    icon: Target,
    title: "Adaptive practice",
    text: "Practice sessions prioritize your weak topics and previously missed questions, focusing study time where it has the most impact.",
  },
  {
    icon: Gauge,
    title: "Readiness tracking",
    text: "Multi-level analytics show readiness by course, domain, and topic — for students, teachers, and department heads alike.",
  },
];

// Static platform facts (not live metrics): the app defines 4 institutional
// roles, and its question-selection service only ever serves approved questions.
const stats = [
  { value: "4", label: "institutional roles, from student to system admin" },
  { value: "100%", label: "of practice questions department-approved" },
];

const LandingPage = () => {
  const pageRef = useRef(null);

  // Smooth in-page scrolling + scroll-reveal, scoped to this page only.
  useEffect(() => {
    const root = document.documentElement;
    const previousScrollBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = "smooth";

    const revealEls = Array.from(
      pageRef.current?.querySelectorAll(".lp-reveal") ?? []
    );

    let observer;
    if ("IntersectionObserver" in window) {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-visible");
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
      );
      revealEls.forEach((el) => observer.observe(el));
    } else {
      revealEls.forEach((el) => el.classList.add("is-visible"));
    }

    return () => {
      root.style.scrollBehavior = previousScrollBehavior;
      observer?.disconnect();
    };
  }, []);

  return (
    <main className="landing-page pro-landing" ref={pageRef}>
      <section className="lp-hero" aria-labelledby="lp-hero-title">
        <div className="lp-hero-glow lp-hero-glow-a" aria-hidden="true" />
        <div className="lp-hero-glow lp-hero-glow-b" aria-hidden="true" />

        <div className="container text-center">
          <span className="lp-badge">
            <span className="lp-badge-dot" aria-hidden="true" />
            Built for Ethiopian university Exit Exams
          </span>

          <h1 id="lp-hero-title" className="lp-title mt-4 mb-3">
            Walk into your Exit Exam
            <span className="d-block lp-title-accent">
              knowing you&rsquo;re ready.
            </span>
          </h1>

          <p className="lp-subhead mx-auto">
            UniPrep pairs AI study support grounded in your own course
            materials with a department-approved question bank, so every
            practice session measures real readiness.
          </p>

          <div className="lp-hero-cta d-flex flex-wrap justify-content-center gap-3 mt-4 pt-2">
            <Link
              to="/register"
              className="btn btn-primary btn-lg px-4 lp-btn-next"
            >
              Get started
              <ArrowRight size={18} aria-hidden="true" />
            </Link>

            <a
              href="#features"
              className="btn btn-outline-primary btn-lg px-4 lp-btn-down"
            >
              See how it works
              <ArrowDown size={18} aria-hidden="true" />
            </a>
          </div>
        </div>
      </section>

      <section
        id="features"
        className="lp-features"
        aria-labelledby="lp-features-title"
      >
        <div className="container">
          <div className="lp-section-head lp-reveal text-center mx-auto mb-5">
            <span className="lp-kicker">How it works</span>
            <h2 id="lp-features-title" className="lp-section-title mt-2 mb-3">
              Four tools that turn study time into readiness.
            </h2>
            <p className="text-muted mb-0">
              From your own materials to governed exam practice, every part of
              UniPrep points at one thing: measurable Exit Exam readiness.
            </p>
          </div>

          <div className="row g-4">
            {features.map((feature) => (
              <FeatureCard key={feature.title} {...feature} />
            ))}
          </div>
        </div>
      </section>

      <section className="lp-statband" aria-labelledby="lp-cta-title">
        <div className="container">
          <div className="lp-statband-inner lp-reveal">
            <div>
              <h2 id="lp-cta-title" className="h4 fw-bold mb-3">
                Start preparing with evidence, not guesswork.
              </h2>

              <div className="lp-stats">
                {stats.map((stat) => (
                  <StatItem key={stat.value} {...stat} />
                ))}
              </div>
            </div>

            <Link
              to="/register"
              className="btn btn-primary btn-lg px-4 lp-btn-next"
            >
              Create your account
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
};

const FeatureCard = ({ icon: Icon, title, text }) => (
  <div className="col-md-6 col-lg-3 lp-reveal">
    <article className="lp-feature-card h-100">
      <div className="lp-feature-icon" aria-hidden="true">
        <Icon size={22} strokeWidth={1.8} />
      </div>
      <h3 className="h5 fw-bold mb-2">{title}</h3>
      <p className="text-muted mb-0">{text}</p>
    </article>
  </div>
);

const StatItem = ({ value, label }) => {
  const numberRef = useRef(null);
  const numeric = parseInt(value, 10);
  const suffix = value.slice(String(numeric).length);
  const [display, setDisplay] = useState(0);

  // Count up when the stat scrolls into view; skip animation for
  // reduced-motion users or browsers without IntersectionObserver.
  useEffect(() => {
    const el = numberRef.current;
    if (!el) return undefined;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      setDisplay(numeric);
      return undefined;
    }

    let frame;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          observer.disconnect();

          const duration = 1100;
          const start = performance.now();
          const tick = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setDisplay(Math.round(numeric * eased));
            if (progress < 1) frame = requestAnimationFrame(tick);
          };
          frame = requestAnimationFrame(tick);
        });
      },
      { threshold: 0.5 }
    );

    observer.observe(el);

    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [numeric]);

  return (
    <div className="lp-stat">
      <strong ref={numberRef}>
        <span aria-hidden="true">
          {display}
          {suffix}
        </span>
        <span className="visually-hidden">{value}</span>
      </strong>
      <span>{label}</span>
    </div>
  );
};

export default LandingPage;
