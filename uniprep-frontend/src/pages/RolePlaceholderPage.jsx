const RolePlaceholderPage = ({ title, subtitle, items = [] }) => {
  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">UniPrep AI</span>
          <h2 className="fw-bold mt-2 mb-1">{title}</h2>
          <p className="text-muted mb-0">{subtitle}</p>
        </div>
      </div>

      {items.length > 0 && (
        <div className="row g-3">
          {items.map((item) => (
            <div key={item.title} className="col-md-4">
              <div className="card border-0 shadow-sm rounded-4 h-100">
                <div className="card-body">
                  <h5 className="fw-bold">{item.title}</h5>
                  <p className="text-muted mb-0">{item.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RolePlaceholderPage;
