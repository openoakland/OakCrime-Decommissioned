## Project status: DECOMMISSIONED

This project has been decommissioned and is no longer maintained. It presents policing-related data from OPD without appropriate context, which may result in viewers misunderstanding or mischaracterizing data in ways that potentially impact historically marginalized and oppressed groups, particularly communities of color. If you're interested in revising this project, please contact OpenOakland's Steering Committee at [steering@openoakland.org](mailto:steering@openoakland.org). Let us know why you're interested and what you hope to accomplish. Consider using the [Project Exploration Worksheet](https://docs.google.com/document/d/1k24P9JiAUEzJLPFRDjVh7aRZexax6NUhfPFLSI3R80M/edit?usp=sharing) to realign this project with OpenOakland's mission and values (required for all new OpenOakland projects).

### Welcome!

We're excited to have your help on OakCrime! This document describes how the
OakCrime team works. We welcome all types of contributions: bug reports, ideas,
features, and feedback. If you have any questions, ask in
[#crime](https://openoakland.slack.com/messages/C040ULV6C/team/U02HPRLSC/) on
[slack](http://slack.openoakland.org).


### Contributing code

Submit a pull request describing the problem you're solving and how you've
solved it. Please make sure that the code passes our code style (via `make
lint`) and you include automated unit tests for your changes.


#### Reviewing pull requests

All pull requests must be reviewed by the @openoakland/oakcrime-reviewers team
before they can be merged.


####  Feature branches

Use a new "feature" branch for each set of changes. Where possible, your PR
should only contain changes specific for your feature and should not include
changes that are contained in another PR. If this is unavoidable due to a hard
dependency on another PRs changes, be sure to make a note of this in the PR
description e.g. "This PR depends on #12".


#### Documentation

Some changes will require updates to the README and other documentation. We want
to ensure that any manual steps needed to run the app are clearly documented. If
you make changes to the `Makefile`, or add a new setting to `settings.py`, you
might need to update the documentation.


#### Merging pull requests

Merges should be done with the standard commit-style merge (as opposed to a rebase or
squash merge) to keep related changes together. This also makes it easy to
revert an entire PR in a single revert commit in the event of a rollback.

In the event of a merge conflict, you're encouraged to rebase your branch before
merging instead of merging master into your branch. This avoids merge bubbles in
the commit log.


### Continuous integration

OakCrime practices continuous integration. Every pull request is tested by our
continuous integration process automatically before it can be merged. All PRs
must pass CI and be reviewed by a team member.
