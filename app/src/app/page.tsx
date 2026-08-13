import { DraftForm } from "@/components/DraftForm";

export default function Home() {
  return (
    <main>
      <header className="site-header">
        <div className="site-header__inner">
          <a className="brand" href="#top" aria-label="PR NEXT ホーム">
            <span className="brand__mark" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <span className="brand__name">PR NEXT</span>
          </a>
          <div className="header-context">
            <span className="header-context__dot" aria-hidden="true" />
            PRESS RELEASE RESEARCH
          </div>
        </div>
      </header>

      <div id="top" className="page-shell">
        <section className="hero" aria-labelledby="page-title">
          <div className="hero__eyebrow">
            <span>PR RESEARCH WORKSPACE</span>
            <span className="hero__eyebrow-line" />
            <span>01</span>
          </div>
          <h1 id="page-title">
            そのリード文に、
            <br />
            <em>次のヒント</em>を。
          </h1>
          <p>
            作成中のプレスリリースから、意味の近い過去事例を検索。
            <br className="desktop-only" />
            伝え方と反響をひとつの画面で比較できます。
          </p>
        </section>

        <DraftForm />
      </div>

      <footer className="site-footer">
        <span>PR NEXT</span>
        <span>Similar press release research</span>
      </footer>
    </main>
  );
}
