# Release Checklist: dev to main

Before promoting `dev` to `main`, verify all items below.

- [ ] `dev` is green in GitHub Actions
- [ ] `pixi run build` succeeds on a clean Pixi environment
- [ ] `pixi run test` succeeds
- [ ] Headless Gazebo launch succeeds
- [ ] Robot model and launch files have been reviewed
- [ ] Simulation smoke testing has completed
- [ ] Physical robot testing has completed if hardware behavior changed
- [ ] Safety-critical behavior has been independently reviewed
- [ ] Dependencies and `pixi.lock` are intentional and reproducible
- [ ] Documentation and migration instructions are current
- [ ] Breaking changes are communicated to the team
- [ ] A maintainer has approved the promotion PR
