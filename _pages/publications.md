---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

You can find all my articles on <a href="https://inspirehep.net/authors/1621061?ui-citation-summary=true">INSPIRE</a>.

{% include base_path %}

<ol>
{% for post in site.publications reversed %}
 {% include archive-pubs.html %}
{% endfor %}
</ol>
