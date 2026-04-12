SELECT ag_catalog.create_graph('org_graph');

SELECT ag_catalog.create_vlabel('org_graph', 'Person');
SELECT ag_catalog.create_vlabel('org_graph', 'Team');
SELECT ag_catalog.create_vlabel('org_graph', 'Project');
SELECT ag_catalog.create_vlabel('org_graph', 'Service');
SELECT ag_catalog.create_vlabel('org_graph', 'Technology');

SELECT ag_catalog.create_elabel('org_graph', 'WORKS_ON');
SELECT ag_catalog.create_elabel('org_graph', 'MEMBER_OF');
SELECT ag_catalog.create_elabel('org_graph', 'DEPENDS_ON');
SELECT ag_catalog.create_elabel('org_graph', 'OWNS');
SELECT ag_catalog.create_elabel('org_graph', 'KNOWS_ABOUT');
SELECT ag_catalog.create_elabel('org_graph', 'REPORTS_TO');
SELECT ag_catalog.create_elabel('org_graph', 'AUTHORED');

-- SCOTUS dataset labels (second example, same graph)
SELECT ag_catalog.create_vlabel('org_graph', 'Case');
SELECT ag_catalog.create_vlabel('org_graph', 'Justice');
SELECT ag_catalog.create_vlabel('org_graph', 'Issue');

SELECT ag_catalog.create_elabel('org_graph', 'VOTED_MAJORITY');
SELECT ag_catalog.create_elabel('org_graph', 'VOTED_DISSENT');
SELECT ag_catalog.create_elabel('org_graph', 'VOTED_CONCURRING');
SELECT ag_catalog.create_elabel('org_graph', 'WROTE_OPINION');
SELECT ag_catalog.create_elabel('org_graph', 'CITED');
SELECT ag_catalog.create_elabel('org_graph', 'CONCERNS');
