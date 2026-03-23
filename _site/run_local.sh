#!/bin/sh

# Requires Ruby 3.1 (installed via Homebrew: brew install ruby@3.1)
# Gems are installed locally in vendor/bundle/ — run `bundle install` first if needed.

export PATH="/opt/homebrew/opt/ruby@3.1/bin:$PATH"
export GEM_HOME="$HOME/.gem/ruby/3.1"

bundle exec jekyll serve --livereload
# Site available at http://127.0.0.1:4000/
