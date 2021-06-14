---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

You can find all my articles on <a href="{{author.inspirehep}}">INSPIRE</a>.

{% include base_path %}

<ol>
{% for post in site.publications reversed %}
	{% include archive-pubs.html %}
{% endfor %}
</ol>