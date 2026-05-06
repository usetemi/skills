[00:00:05] CHRISTINE: Hey everyone, welcome back to OpenAI Build Hours. I'm Christine, I'm on the startup marketing team, and today I'm joined with Charlie and Ryan.

CHARLIE: Hey folks, how's it going?

RYAN: Hey everybody.

CHRISTINE: Awesome. Charlie is on our Dev X team and he will be leading the session. Ryan actually came all the way from Seattle to be with us live in the studio today, and he's going to be chatting about the future of work. Today's session is all about the API and Codex. And if this is your first Build Hour, the goal of the session is to empower you with the best practices, tools, and AI expertise to scale your company using OpenAI APIs and models. This session in particular is really going to teach you how to use Codex for all of your engineering work and what is the next step in using Codex that goes beyond pair programming.

Here's a snapshot of what you can expect today. We're going to spend five minutes on all the new features we launched across Codex and the API — lots to share on the app as well as a new model that just came out last week, so perfect timing. Then we're going to dive into a demo on agent legibility score, which is going to be super practical for you to apply right away to your team. Then Ryan is going to talk about harness engineering. We released a blog on harness engineering from Ryan, who's going to be in person talking about what this means and how you can apply it to your team. Then we'll save some time for a customer spotlight — Basis will be joining us live, and we're really excited to have co-founder Mitch to talk about how he uses Codex with his engineering team. And last but not least, we'll save 15 minutes for Q&A. On the right side of your screen there's a Q&A chat box where you can submit your questions. We'll answer them during the session and then save a few to answer live at the end. So with that I'll turn it over to you both.

[00:01:56] CHARLIE: Thanks Christine. Let's kick off by talking about what's new in Codex. We've really entered this third phase of using AI for software development. The first phase was autocomplete — the ghost text. The second phase was pair programming, where you'd have a model sit alongside you in your IDE and work on generating code and potentially merging it into your existing code. But we've really come into this new era of agent delegation, and that's where you can use things like the Codex desktop app to manage multiple agents across increasingly bigger tasks and workflows.

RYAN: I'm sure you've all felt this, but there was a huge step change in capability with GPT-5.2, and with GPT-5.3 and GPT-5.4 on top of that, we have only trended increasingly into this long-horizon, full-delegation-to-the-agent direction. For me as a builder this has been a fantastic thing — it empowers me to do more and to do more quickly.

CHARLIE: Absolutely. It's been kind of surprising for me in terms of how quickly my own workflow has changed, especially with the Codex desktop app. It's mostly replaced the IDE for me at this point.

Just in the last couple of months, as you were mentioning, GPT-5.3 for Codex which got even faster, the Codex app which is now about managing agents rather than necessarily living in your terminal or your IDE, and we just released GPT-5.4, which we'll get into in a little bit.

We'll be using the Codex app a lot today, and if you were not aware, it's now available on Windows, which is a big milestone for us.

RYAN: Super excited about this app. And one thing that is truly amazing about it is it has Windows-native sandboxing through and through — it doesn't rely on WSL and allows you to build with Codex in ways that are native to your local development best practices. I think it's super cool that we're bringing all the power of Codex's security model and best-in-class coding capability to developers on Windows. We really aim to meet you all where you are to help you build.

CHARLIE: Yeah, so much of the world is building on Windows, and we'd really love it for you to check out the latest Codex app.

[00:04:11] The app itself has a few new features in the recent weeks and months. The big ones are skills and apps. You can bring capabilities and expertise via skills — there are a number of them that are recommended and come pre-available inside the app. And then we also have apps, which you can share across both ChatGPT and Codex. These were previously known as connectors, but you can use them to connect ChatGPT and Codex to the tools you use every day.

RYAN: Skills are super powerful. The way I think about them is context that we give to the agent to show it what end you use the tools you have, and how to use your tools well. The fact that we're bundling a bunch of them with the Codex app means you get all the best parts of how we use our tools well to supercharge your own workflows.

[00:05:01] CHARLIE: Let's talk about what's new in the API. The big news from last week is GPT-5.4. It has native state-of-the-art computer use capabilities — you'll see us refer to this as CUA, computer use agent. It supports up to a million tokens of context, and it has a new tool search tool. In practice, a lot of the bleeding-edge builders were using hundreds and hundreds of tools, which was potentially creating issues with context management. So we now have tool search, which can help you namespace those tools, and the agent can intelligently and progressively expose those to get the tools it needs.

RYAN: The term of art here, if you've heard it, is progressive disclosure — the idea that not all tools need to be in context all the time for every task the agent does. So instead of giving them everything up front, we hide all the tool descriptions and individual calls behind something that allows the agent to do a little more natural discovery and choose which parts it pulls into context intelligently.

CHARLIE: Exactly. And it's the most token-efficient reasoning model. You can see on our benchmarks it's achieving the same performance as Codex GPT-5.3 and GPT-5.2, but with a fraction of the token consumption and latency.

[00:06:24] We're not going to touch on all of these today — I'd encourage everybody to check out developers.openai.com to look through the API changelog. But some of the big things we've shipped just in the last month alone: the CUA API, which I mentioned, which really beefs up the ability for developers to manage browsers and computers. We have a new code mode where the model can generate JavaScript for you to run in a REPL, which dramatically speeds up the time it takes to do things. Previously you'd have to click and screenshot and find coordinates, and now you can compress all of that into a single JavaScript execution statement.

RYAN: Love to give the model more tools and let it cook.

CHARLIE: Yeah. We have skills and Hosted Shell, which we'll be using in this demo. With skills, you can upload to create a skill ID which the model can reference. Hosted Shell gives the model a container environment it can spin up, and it can actually execute bash commands inside that container environment. And then we also have WebSocket mode, where if you're building an integration on top of the API you can switch over to using WebSockets. For extremely tool-heavy use cases, we find that it improves latency by 20 to 30%.

RYAN: One of the things in here that I'm most excited about is the Hosted Shell tool, because it takes all the magic of coding agents — of giving them a computer and a shell to go solve really complicated problems — and puts it in our API in a way that is super customizable, able to be embedded deeply into the agents you build, and optimized to the way you evaluate the workflows you're building toward. And if you want to use the Codex harness itself, we do make that easy too by shipping adapters with the Agents SDK to allow you to give Codex to your agents as well. So we kind of give you the best of both worlds with both of these options.

CHARLIE: 100%. Our vision is to meet developers where they are and give them primitives, whether it's hosted on our infrastructure or running locally on yours.

[00:08:24] Cool. So with that in mind, let's jump into our demo. One of the principles we're going to talk about in the harness engineering portion of today's Build Hour is trying to make repositories more legible for agents. We had this idea of using Codex to actually make an app that will score a GitHub repository along a certain set of metrics that we've predefined.

RYAN: This is exciting because it's an easy checklist that we're going to put together that will guide you in the direction of trying to remove humans from the loop from different parts of the code authoring process.

CHARLIE: Yeah. So I'm here in the Codex app. I've got a new folder here. In the interest of time, I've actually created a plan in advance for the agent to go ahead and implement. This is the kind of thing you could easily create yourself with plan mode in the Codex app. But we've got about 10 minutes here, so now I'm going to go ahead and tell it "implement plan.md." Behind the scenes, the model is going to think for a minute, decide to explore the workspace, figure out what files are available, what the current state of the GitHub repository is, and take a look at what it can do.

RYAN: Yeah, this is super exciting because the app makes this much more digestible for me. It kind of lifts me out of my terminal and puts me into a higher-level operating mode where I'm more reviewing the agent rather than being deep in the weeds with it. This is the transformation in how we interact with this tool, enabled by the huge step change in capability that really only became possible this year.

[00:09:59] CHARLIE: There's something interesting here — the model has actually realized we built a previous version of this app in an archived folder, and it's going in to take a look at that code to learn from previous runs. This is a peek at an interesting technique I've used to build some agents for myself, which is to basically provide pointers to previous trajectories, previous iterations of the task. This serves to give the model a reference for how the task was completed previously, what it might learn from those previous trajectories, and gives you a very cheap way to implement what we call episodic memory — a way for the agent to improve the way it works over time while completing similar tasks.

[00:10:45] While it's working, let's take a look at some of the things going on in the Codex app. At the bottom we've got a task list. This is not anything that we generated or specified — this is just the model internally saying "here is the road map I need to complete" and giving us some visual indicators on what it's doing.

RYAN: Yeah, this is distinct from plan mode. It's really just a nice way for me to have a high-level sight of what the agent thinks is up next for it. And I use this as a tool for myself to figure out whether or not I should interrupt or provide steering to Codex, as opposed to just letting it cook. It helps me have confidence that the agent is doing the things I expect.

CHARLIE: Yeah. And so if we open up a new thread, we can see that if you want to toggle on plan mode, it's really powerful for getting context, asking you what direction you want to take things in, and developing a really thorough plan. We now have speed — you can choose whether to run Codex in standard or fast mode. Fast mode is fantastic, but it does consume your usage a bit more quickly. And then we have the ability to toggle some of the permissions and settings.

I love the worktree capability of the Codex app. Worktrees, if you're not familiar, are essentially like git sandboxes — they allow you to work on multiple things simultaneously within the same folder without stepping on or clobbering changes in a different task thread.

RYAN: Yeah, if you've seen folks with five screens and 18 tmux tabs, worktrees is what they're using in order to go in parallel. Getting your codebase working with worktrees is one of the steps you can do to move toward a harness engineering mentality — basically make it really cheap to work on multiple copies of your code at once.

CHARLIE: And the Codex app has a really great handoff feature where if you're in a worktree and you do want to bring those changes back to your local branch, you can click a single button to do so. Or if you want to push them back to the worktree, you can click a single button to do so. There's a lot of great git support in here. This is a pretty simple repo, so we just have the main branch. But you can easily commit and push just from the app, open these files in your IDE of choice. There's a terminal so we can take a look at what's going on. There's a diff panel — in this case we've got quite a lot of changes now. It's written 8,200 lines of code just in the few minutes we've been talking.

Over on the left we've got the skills and apps we were talking about earlier. I really love the set of skills that we provide out of the box here, as well as the apps you can go ahead and install for yourself.

RYAN: One neat thing with Google Calendar in apps is it should maybe help get you thinking about ways you can use Codex to automate other parts of your work other than just the code you're writing. I've set up a couple of tools to help me digest my calendar and make sure I'm allocating my time effectively — really cool to unblock the other parts of my job with this tool.

[00:13:53] CHARLIE: I love that you brought that up. Let's talk about automations, which to me is like the killer feature for the Codex app. Automations — you can see a lot of my messy inbox here — is a way for you to just run a command on a regular schedule. It sounds simple, but I've been surprised at how powerful it is in practice.

RYAN: Yes. One I run all the time is to have the Codex app review all my open PRs and make sure that they're mergeable, that they haven't come into conflict. Codex is really good at resolving merge conflicts, and I am more than happy to delegate this work to Codex to make sure that I'm always unblocked to smash the merge button as soon as my code is approved.

CHARLIE: Yeah. In my case, my most popular one is Slack management — just checking on work streams I've got going on or updating to-dos from Slack. I've seen other folks at OpenAI use it for things like, take my most recent PRs and just review them for any potential bugs, or look at my Git history for the last 24 hours and surface a quick summary for standup today.

RYAN: Amazing.

[00:15:03] CHARLIE: Okay, let's take a look at how the app did. It looks like it went ahead and built something for us. It did some testing — it ran lint, test, build. And so we can go into the repo that I asked it to make and take a look at what it's got.

Cool. It went ahead and one-shotted this app for us. There's a lot going on here, but I'll give a quick overview. The way this is meant to work is we put in a GitHub repo and maybe some custom instructions. It's going to analyze that GitHub repo — again, we're using Hosted Shell — and score it based on these seven metrics for agentic legibility.

RYAN: I wonder what would happen if you put the Symphony repo in here.

CHARLIE: Yeah, great callout. I actually had already loaded this up. Symphony is a repo that we just open-sourced last week alongside this theme of harness engineering. I've previously tested this so I actually know to tell the model to only score the Elixir folder.

[Technical difficulty — missing OpenAI model / environment variables]

RYAN: Power of live demos, folks.

CHARLIE: I know — you can never be too confident in what's going to come back out. All right, let's try that one more time.

RYAN: I do like that the agent biased toward configurability, though. That's a nice touch. Very 12-factor app style.

Okay, it's going ahead. Why don't you tell us a little bit about Symphony?

[00:17:03] RYAN: So Symphony is kind of the next step that came out of the work that we did in this repo, which is very bootstrapped for harness engineering. It takes this idea that if we have enough guardrails around Codex that it's reliably producing code that's going to be accepted by all the human engineers and agentic reviewers on my team, let's remove the humans from the loop entirely on poking at their terminal and instead have them working at a much higher level defining work in Linear. Symphony is an orchestrator that manages advancing that work through the ticket queue, making sure that Codex is spun up in a worktree, implementing that code, putting it up for review, going back and forth with CI and agentic code reviewers, and only bringing the humans into the loop once all our previous constraints are satisfied. This allows me to truly focus my time on the hard stuff — prioritizing work, reviewing work, and making sure that the work we're doing is accruing value to the actual products we want to build.

CHARLIE: Yeah.

RYAN: And it's really nice to be given a fully baked PR and be able to make a cheap yes-or-no decision on whether or not I can merge, and then Symphony will manage merging it for me.

[00:18:20] CHARLIE: Nice. And it looks like — yeah, this is reflective of the fact that you've put a lot of thought into those design patterns. Our app here gave you a B-grade on your agentic legibility.

RYAN: Nailed it.

CHARLIE: Let's take a look at what it scored and its recommendations. Bootstrap Self-Sufficiency: basically, can the repo get set up from scratch? Is there external knowledge you might need to know, or commands you might need to run to make this work? Task Entry Points: is it easy for the agent to just run `make`, or `build`, or `lint`, or that sort of thing? Validation Harness: how easily can it check the changes that it made?

RYAN: Hard to know if you completed the job if you can't measure that the job is done.

CHARLIE: Exactly. Linting and Formatting: this one found that you had a linter but maybe it wasn't as obvious to the model where to find it and how to expose it. In practice, linting is probably the best low-hanging fruit to tackle — it saves so many cycles because the model can just check its work really cheaply.

RYAN: That's right. And it's super easy to add leverage to your codebase by vibe-coding some new lints. Codex is really good at this.

CHARLIE: Yeah. Is there a map for the agent to take a look at where things are? Are docs structured easily? And then are there any decision records present in the repo? In this case, that was the only one you guys missed on.

RYAN: Yeah. Artifact of open-sourcing things. Sorry, folks.

CHARLIE: But it made those recommendations. And you can see over here — these are logs from the container, the Hosted Shell happening in the background. If we go back to the Codex app, we can see that in firing off this Responses API request, we sent it a model, we specified this skill ID which has all of that knowledge of the metrics in the background. And the team has actually put a lot of thought into safety and security around this stuff. It's not trivial to just say, "Let's open up all network access." So we did have to specify a whitelist of domains that we wanted the shell to be able to access.

RYAN: I think it's super nice how high-level the container API is. It allows you to get very good secure defaults that empower the agent to cook while maintaining the safety, security, and invariants that you want — because fundamentally these agents are going to do what they do, and we need to make sure we put them in the right environment to do that.

[00:21:05] CHARLIE: Yeah. So we'll have these slides here — these are the legibility metrics that we started on. But ultimately this was kind of a one-shot example. It's a single plan we one-shotted, we vibe-coded this app. I think the more interesting question is: how do you continue to build bigger things? How do you extend that vibe-coding session into something much much larger?

[00:21:30] RYAN: That's right. This is why I'm excited to talk today about harness engineering — what it is and what we learned while operating on a project that my team took on for about five months, where we had the hard constraint that no humans would write any lines of code. We ended up with a product that we're shipping internally today that is about a million lines of code, where all of it — 100% of it — has been written by Codex. This has been a very interesting experience as an engineer because I can't actually clack on the keyboard in order to make progress. I have to step back and think at a systems level about how to enable my team of agents to go do the thing. Agents see the world and code slightly differently than the humans I would normally have on my team. So over the course of this project, we've been figuring out a bunch of patterns on how to refine the output of these coding agents so we can get to merge over and over again.

One might imagine that a million lines of code entirely written by agents — that's got to be a hot mess, right? How do you manage that and make sure it's good?

CHARLIE: Yeah. I believe the term for this is AI slop. And one great thing is that code is now so much cheaper to produce than before. You can simply say "I do not tolerate AI slop" — which to me is slang for "code I don't like." If you can articulate what it is about the code you don't like, the next step is to write that down in documentation, or in a bespoke code reviewer agent, or in tests or lints. If you can say what it is you don't like about the code being produced, you can work toward encoding those non-functional requirements in your codebase to just ban that code from happening in the first place.

One nice example I have here: one common pattern we see is that coding agents like to optimize for local ease of use, which means you can end up with several copies of the same routine in your codebase. We ended up with very many copies of a bounded concurrency helper. But only one of them is the one we've invested in to instrument with our OpenTelemetry stack. So we have a lint that basically bans this function, in various shapes, from being defined anywhere else except our canonical async-utils package. And this is just a vibe-coded ESLint rule which we can assert is 100% covered — because we can just do that — which makes Codex exhaustively write tests for the positive and negative cases. This is what it means to dive deeper into the systems thinking within your codebase: observe the mistakes or classes of misbehavior that the agents are making, and do what it takes to statically disallow them.

This has been really really cool because it allows us to actually encode what it means to have trusted engineering in the code. It's just not possible for AI slop to enter the codebase.

One other neat thing is that these things have stacked incredibly well. We've observed that as we've onboarded engineers to the team, they each have a different set of experiences and ideas of what high-quality correct code looks like. Each one of the engineers who's joined my team is able to reduce slop in a unique way. And because everyone is invested in putting that knowledge into the codebase, it means everyone else's coding agents have the best of everyone on the team.

[00:25:28] RYAN: Yeah, why don't we dig into some of that Codex usage.

So when we started this was very very slow. Codex did not have a good idea of what my acceptance criteria was, so I often had to double-click into a task to build some building blocks to get the refined output I actually wanted. But once I had invested in those building blocks, I went from maybe a quarter or half an engineer's worth of throughput at the beginning to three to ten engineers' worth of throughput per engineer. And one other neat thing is that as I've added members to my team, our throughput has actually increased because we have that flywheel of subsequent knowledge that every engineer has, impacting everyone's coding agents for the better.

Another neat thing: because the only way to get code that is accepted is to get the coding agent to do it, we've had to pull a ton more context into the repository than I otherwise would have in the past. A good example here is I partnered with our security engineering team to upgrade our app to the blessed cryptography library that we support. But that decision happened in a Slack thread buried in our team channel two months ago. We hired a new engineer onto the team and they were working in this part of the code and brought in a new npm package for some of this functionality. I knew when I reviewed the code that this was not aligned with our engineering practices. But this is not the engineer's fault. It's not Codex's fault. That information just wasn't encoded in the constraints of our system. So I went back to that Slack thread and did `@codex please add guardrails to our codebase`, reflected that knowledge back in, and then redid the change, which then resulted in more aligned output because it used the blessed cryptography library we were supposed to.

CHARLIE: Wow. So it sounds like you're heavily relying on these integrations, these apps into Slack or Linear or whatever else, to get context back and forth.

RYAN: Yeah. And it's super cheap to do this. I `@codex`, I go away for 5, 10, 15 minutes, and I come back with four proposed PRs on how we can make our code higher and higher quality in the future.

[00:27:49] The other pattern that was really really neat: we have a lot of context in the codebase — too much to put in an AGENTS.md file. Just talking about our security best practices is a 250-line markdown file. Same for what it means to write reliable code. I'm sure all of you in your past have gotten a page that was resolved by adding a retry and a timeout to some network code. We all know this, but still code ends up in production that does not have retries and timeouts, and code produced by Codex is the same. So writing that non-functional requirement down, giving the agent pointers in AGENTS.md on how it can look at our best practices for reliability, and then reflecting that back into the agent in a reliable way via a code reviewer agent that operationalizes around reliability and leaves comments on PRs that our primary authoring agent is forced to read — that means we can steer the system to converge around our set of guardrails in a way that's actually higher reliability than having the humans do it. Codex is very very patient and willing to take as many code reviews as we can throw at it, whereas I might get frustrated and just yolo-merge it anyway. So we do end up with very high quality code as a result.

Another neat thing: we had a new engineer join the team, very product-minded, who was frustrated that Codex was not able to effectively smoke-test changes to critical user journey flows in our app. So they pointed Codex at the codebase, asked it to spider through all our user-facing features, write product specs for them, write manual QA plans, write the user needs that these flows address, and then pushed that into a bespoke reviewer agent to look at every PR and generate a manual QA plan — which Codex is then able to look at in order to validate that its changes work end to end and are aligned with our app's functionality.

What I find really fascinating about this kind of setup is: normally these things maybe exist in Slack or in conversations. We've never taken the time to actually write them all down and encode them in our code repositories. But to your point about it being now so cheap to generate these things, that is a new avenue of documentation.

CHARLIE: Yeah. If you want Codex to be an effective member of your team, you need it to know all the things it takes in order to have acceptable code in order to merge. It really is about the non-functional requirements in order to get truly aligned output from these agents.

[00:30:33] RYAN: So, as we've onboarded new folks to our team, they each bring their own experience and expertise. I myself bias more toward backend infra and architecture, which means I just did not have the know-how to get high-quality React code out of Codex. But as soon as we hired someone with deep front-end architecture experience and they started reflecting that knowledge into the codebase, all of a sudden hooks were getting decomposed to a single hook per file, we were getting small components that were easily testable via snapshot testing and composed together well to have smaller files that are more efficient for the agent to page into context. And with each subsequent engineer on the team, they encode more and more of their taste and expertise, which means everybody's coding agents get more effective.

CHARLIE: That's so cool.

[00:31:28] RYAN: So some key tips on how you might apply some of these patterns in your own work. You should check out the Codex repo, which already has much of this in it. Just clone it and ask Codex to explain how it is structured and to teach you about the best practices the team has used. Another cool thing I'm seeing all over X right now is folks are literally taking the link to the Harness Engineering blog, giving it to Codex in their repository, and saying "make my codebase more agent-legible, make it do this" — and folks are getting good results that are improving the autonomy, quality, and long-horizon task execution of Codex. Super super cool that we can essentially ship prompts to the world to help everyone be more effective with Codex.

CHARLIE: Yeah. And I love that it's this shift — from coding on the keyboard to now orchestrating at that next level, which is Symphony. That's right. That's how we get to the repo name.

RYAN: That's right.

CHARLIE: All right. I'll hand it back over to Christine.

[00:32:31] CHRISTINE: Awesome. Thank you guys for walking us through that. And now for our customer spotlight — really excited to welcome Mitch, co-founder of Basis. So we're gonna pop out of this screen share and then Mitch should be joining us on stage.

MITCH: Hey guys, thanks for having me.

CHRISTINE: Hey Mitch!

MITCH: I think I'm going to be saying a lot of the same stuff Ryan and company have been saying on putting stuff in the repo and whatnot, but this will be a fun discussion. Let me see if I can share my screen. So I had Codex make a quick presentation here. Can you guys see that? Yeah. So I'm just going to quickly go through and talk about some of the stuff we do, which I think is very similar to the harness engineering work, and both on how we do it for engineering in our codebase but also actually at the company level — and how I think you can think about using Codex beyond just the codebase.

[00:33:46] I realize let me give a quick introduction of myself. I'm Mitch, I'm one of the two co-founders of Basis. Basis is essentially an agent platform for accountants. We recently raised a Series B, and we are very very focused on engineering our company in such a way that we can move extremely fast. The reason I always tell people this is so important is that our ambitions are so large that if you think about the scale we need to be at in very short periods of time, it would literally be beyond the laws of physics to hire that many people. So we can't rely on that. Instead you have to really engineer your company and your codebase to have as much output as if you were a company that was 10x the size.

[00:34:47] Going back onto the codebase side, doing that really does require a big mindset shift. Part of what you just heard about from the Symphony side is that people need to be able to shift from doing to managing. And that's actually a very hard paradigm shift to make, and different people are able to get to it at different speeds. But that shift is hard to make — whether it's engineers doing it or people on the sales team or the post-sales team — if the agents aren't actually working well. So it's hard to convince someone to let an agent write the code if the agent isn't actually writing code well.

And you have to have the mindset shift about how do you build for agents, not just for people. You want agents to have the ability to self-verify. You want them to understand what the different intents are that people are giving them. And even then, if you're in a production codebase or a larger company, you need abilities to collaborate so that one person's preference of how some agent behaves doesn't override another person's preference.

[00:35:57] So what do you actually need to be true at the codebase level for this to work? You need to have good standards in terms of how you want the code to be written. That needs to be turned into good context. And then you need good processes around this to make sure that context is kept up to date. And then you need internal setup that's easy to operate. If you have a bunch of dev tooling that has no MCPs or ways to integrate with your agents, they're not going to be able to validate their work or use the same tooling that a developer would. For example, at Basis we have something called Satellite, which is a single MCP that essentially wraps all other MCPs so that developers only have to integrate with one MCP rather than 50.

[00:36:46] Why is Codex really good at this? Specifically for production codebases, if you want the agents to be really good you need to get really good at instruction following, and Codex is very good at instruction following — to the point that it actually forces you to be even more precise in your documentation and more precise in your context so that Codex follows your instructions. Codex is really good at gathering context ahead of time. Ryan was talking earlier about progressive disclosure — if you're going to have lots of progressive disclosure, which is really important for any level of complexity, you want the model and the harness to be good at going through that progressive disclosure to gather the context it needs to do tasks. Codex is excellent at that. And you need to be good at making decisions in areas of ambiguity, and Codex is really good at that.

[00:37:41] So let's talk a little bit about Basis and I'll go into a couple demos here on how we do this. In terms of how do we set those standards: we focus on AGENTS.md files. We have an AGENTS.md at the root and then we have AGENTS.md in different modules throughout the codebase, with the principle that if the information is specific to that module, you put it in that module's AGENTS.md — versus if it's generic across modules you would put it into a skill.

I think it's super super important that you set these standards, treat them as canonical, and then build processes to keep them updated. Maybe I'll show you one quick example here. I have to be careful going into the live stream on what I can demo, but just to show — so this is a skill that I have. You can see it's called paper-updating. I'll explain what Paper is in a second. But this is a skill we have on how to update something we internally call Paper. The key here is that there is an owner right there in the skill's front matter. What that means is you can have very distinct responsibility for who is responsible for different skills. So for example, let's say you were running an agent that was going to look at the different skills and see, hey, are there any skills that have descriptions that conflict with each other? Making sure the skill knows who the owners are so you can Slack them or something like that.

[00:39:33] And this gets to this internal tool we've built called Paper, which I'll just show you for a second. Paper is essentially a way to — if you're going to have all of the context in the repository, which we want to do — our monorepo is called Arnold, because Arnold was the most popular name of an accountant in the US according to ChatGPT in like 2023. So that's why it's called Arnold.

If I go to Paper and show this to you quickly — so here is Paper, and as you can see we have, you know, codebase engineering at Basis. I'm not going to show you all the different skills, but I already have it preset up with the skill I was just looking at. So it's very clear who the owner is, what the flow is. And this allows us to really easily make sure that you're not getting slop into the codebase, that you're actually keeping it updated, that people are actually looking at the skills and able to read it.

[00:41:01] So that's just an example of how we have skills. And then we also use sub-agents. Codex, as of recently, supports sub-agents. Codex is really really good at enforcing standards for sub-agents, and we use sub-agents very heavily. Some of the sub-agents that we use: we have a specific sub-agent whose job it is to enforce standards — so Codex will do a pass and then go and call the standards-enforcer sub-agent if there are any things Codex might have missed in terms of our standards. We have a sub-agent for babysitting pull requests in case Codex wants to send someone off to go do that. Sub-agents are a really really good way to take flows that Codex is amazing at, but you want to be really sure about, and put them in a specialized sub-agent that Codex can call.

[00:41:27] A couple other quick things and then I'll go into a couple more quick demos. I think it's really important that agents have the opportunity to actually verify their own work. Codex is really good at going for long periods of time, and one of the things it's really good at is using tools and context to make sure it's doing a good job. So you need to give it ways to do a good job — that includes tests. Can it quickly run tests against the work it's doing to validate itself? One flow I like doing a lot is having a more test-driven development approach where you don't just have a product spec, but you actually have a list of tests that Codex can go and generate for you that outline the intent of the change, so that Codex can ensure that the different user flows it is making actually work by the time it comes back to you.

[00:42:22] Okay. And lastly, I think one of the big things that starts to happen once you actually have Codex writing all the code and executing things really well is that decision-making starts to become the main bottleneck on your velocity. So we have been trying to do things on our setup that allow decision-making to actually start becoming faster as well in working with Codex.

One of the things we do is we have this concept of `.notes`. `.notes` is essentially a way where if you're working with Codex and you have some decision — let's say you told Codex "you should be doing it like this" — Codex will put decisions that were happening throughout the session into `.notes`, which is a part of the repository. Think of it like commit messages, but commit messages that Codex can write to whenever it wants rather than only when it is making a commit. This creates a full kind of history for every commit of what decisions were made in that session, which you can use as a historical debugger. So if you're going back to a historical commit, you can say "why did Codex, or whoever made this commit, implement it this way not that way?" — you can look at the note in the notes folder and it will tell you.

And obviously specs that live in the repo are really, really key. As a quick example of that, I have a hero product spec that I put for Paper here. If you kind of look at it on GitHub, it's sort of not the greatest or easiest thing to read — it's hard to leave comments. And so one of the things we built internally is the ability to go and collaborate on specs right inside of your codebase. So I can go here and leave a comment — "test Codex comment."

And this will now leave a comment that is directly inside the codebase. So all the commenting, all the resolutions, all the interactions, all the planning actually happens literally inside of the codebase. And if you go here, you'll see the comments. It's just a cool internal tool we built. The reason for this is specifically for the purpose of — as Ryan was talking about — bringing stuff inside of the codebase so that we can have as much context there as possible, so that Codex has all the context it needs to help us make decisions and implement things.

[00:45:01] And then lastly, and Christine I'll hand it off to you after this: I think it is really important to not stop at the codebase. For the company, we think about this mindset of having context in the codebase not just as a production code question — we think of it as a company context question. We have two repos in our company. One is called Arnold, which is our monorepo, and the other is called Atlas. Atlas is the monorepo of all the company context that is not in our production repo. Things like, if I go here — here are some of our operating principles, which you can also find on our careers page. And having that very clearly in a codebase means that, say, you're trying to work with Codex to help plan — it can go and read all the information about the company in order to help make decisions about different things.

Once you start realizing this, you can do a lot more. So maybe I'll just show you one quick example of what that allows you to do. If I were to go and pull up Codex — since we used the app earlier, I'll use the CLI quickly — I have a skill in my personal setup that's called "start my day."

What "start my day" does is it runs through my morning routine — grabs all the context from the last 24 hours, refreshes a bunch of different things, handles weekends, et cetera. I'm not going to actually let it run because then it'll show some information, but it can do this really, really well because it has all of the context it needs both from my personal notes, our company repository, and Arnold.

So I'll pause there and give it back to you, Christine.

[00:47:34] CHRISTINE: Awesome. Thanks so much. We have about 10 minutes left for Q&A. Mitch, if you want to stay on, we had some come in through the chat specifically for you. We'll just go back into the screen share.

Cool. First question, Mitch: how did you use Codex to generate the deck?

MITCH: Yeah, you can go and have it make PowerPoint in Python, but that was just HTML. So I just told it to make HTML, and I voice-typed all the context about the thing I wanted. And if you notice, I told it to go find what the OpenAI fonts are and find a similar one.

RYAN: I do this all the time too. It's super good at just vibing a bunch of single-page React slides into place.

MITCH: Oh, totally. Yeah.

[00:48:33] CHRISTINE: Nice. Okay, next question says: "Shout out to Mitch, met you at an event in New York City. This is awesome. A few questions: is there any checkpointing or ability to revert? From a management perspective, are there any plans for collaboration features like shared threads? Can Codex execute browser previews or browser automations?"

RYAN: I can take that last one. Codex can definitely execute browser automations. There's a Playwright skill that's been around for a little bit, and then we just released a Playwright interactive skill which takes it even further in terms of the depth that Codex can go in using the browser. Personally I do it whenever I'm doing front-end work — if I have feedback for Codex, if it's gotten a box wrong or an alignment wrong, I'll tell it to use Playwright and just keep iterating and screenshot it until it feels confident it's got it correct.

I think the others — in terms of checkpointing and shared threads — I'm not sure about shared threads, that's a great question. In terms of ability to revert in the app, you have everything showing up as staged or unstaged files, so it's very easy to just click and stage or unstage stuff. Or you can simply tell Codex, or have it in your AGENTS.md, to "git commit everything as you go." Once you set up that scaffold, it can take care of itself.

MITCH: Yeah. I definitely let Codex commit its own work, and I give it a skill for what our expectations are around commit messages, and the progress and granularity of those commits works pretty well.

[00:50:03] CHRISTINE: Okay, next question: as we move from AI pair programming to full agent delegation, what are the key design patterns that make an agent reliable enough for production systems?

RYAN: What I've found is it is highly beneficial to put in pretty rigid architecture patterns that you would expect to deploy in a company of a thousand or ten thousand engineers — which means I've dived really heavily into separation of concerns, proper package layering, making sure that business domains have high cohesion, encapsulation, and boundary separation. This helps with context management. If you're working in one set of business logic and the agent can take as given an opaque interface that it can rely on invariants for, then for example if I'm building a task summarization feature as a core set of business logic, if it can accept a dependency on an inference interface without deeply understanding it, I've limited the amount of context the agent needs to page in. And this is sort of the same pattern as progressive disclosure that we're doing in the docs. Being able to structure the codebase in a highly opinionated way also permits those code-as-prompts to follow the same sort of pattern.

CHARLIE: Cool.

MITCH: Yeah, we by the way did far more refactors than you would have five years ago because of this. I totally agree.

[00:51:37] CHRISTINE: Okay, next question: "How does your team maintain agent instructions? Does each engineer provide their own personal set of instructions, or do instructions get shared and version-controlled? How does the team sync up on adding or improving instructions?"

RYAN: So everything lives in the codebase, which means on my team we have very few personal AGENTS.md files or personal skills. We treat this as a way to encode leverage for all the agents that are operating on my team's behalf. We've also converged on only a handful of skills that are pretty general — we have a skill for making PRs, a skill for landing changes and deploying them, a skill for making commits, a skill for doing code review, a skill for analyzing the architecture of proposed plans, and really that's it. Any additional leverage we want to give the agent either goes into reference documentation that goes with those skills, scripts that go with those skills, or the documentation and tests in the repository itself. And this has the benefit of getting things out of individual teammates' heads and into a space where everybody's agents can benefit from shared knowledge.

We have a bias toward really high-frequency in-person standups. We have a 30-minute standup every day, which is maybe something a little bit different from how folks have been working recently. But the code velocity is so high and each of the engineers is disconnected enough from the code that it can be weeks before I realize core architectural patterns have changed. So bringing those to synchronous time for the humans to collaborate has made a ton of sense for us.

CHRISTINE: Mitch, is there anything different that the Basis team does here?

MITCH: No, I think it's all the same. The thing I'd actually be curious to ask about is the thinking between putting front-end or back-end standards into docs versus a skill. We put a lot of that in skills. And then we have docs meant to be docs, kind of meant for humans — still useful for agents, but we keep a lot of that in the skill. So there would be like a front-end skill that the agent — any time Codex is touching any front-end code, it will go and look at it, and that will have a bunch of references under it that have specifics on different parts of the front end depending on what it's doing — assuming it's not completely scoped to a module, in which case it'll be in the AGENTS.md.

RYAN: Yeah, we instead put all of that task-specific expertise in the documentation hierarchy and focused the skills on high-level operating modes. So we'll have a principal review skill that the human can steer to look at specific documentation, but it's otherwise just a general mode with which Codex should be approaching the task.

MITCH: Cool. That's cool.

[00:54:44] CHRISTINE: Worktrees sound cool. Can you demo that quickly?

CHARLIE: Sure. Yeah, let's take a quick look. Let's go back to Codex. The way worktrees work: right now I just pick a new worktree, and then I'll say "modify plan.md to be shorter." I'm going to toggle off plan mode and put it on low just so it's fast. But you saw briefly there it created a new worktree, and now it's going to go ahead and start making changes. Yeah, it's smart enough to know that it should read it first. It's taking a look — I think it's looking for which one it should edit, right, because we previously had some archive ones.

Basically, one thing that didn't happen in this branch is we didn't automatically bring in our existing diffs. All the changes that happened locally are currently separate from this worktree. So that way I can work on this branch there. There's an option to bring those changes if you want them, but by default it'll take the clean main checkout, or whatever branch you want, and go ahead and do it. So it's going to modify these files. And then we'll have the ability to either spin off a branch and create it later, or once it starts making diffs and if you're on a separate branch, it'll let you decide whether you want to hand those off to your local environment.

RYAN: Yeah, the way to think about this is I can have multiple working directories with multiple different branches of the repository on my file system at the same time, without having to clone the repo multiple times. These git commands are pretty fiddly. I hate using them. So it's great that the Codex app is just going to do this for me.

CHARLIE: So it made a bunch of changes here, but those are not going to be reflected in our main thread.

[00:56:34] CHRISTINE: Okay, next question. We'll rapid-fire through these as we're almost at time. Due to progressive disclosure, should you just enable all skills so they can be called if needed?

RYAN: I would say yes. The thing to invest in is short, high-quality descriptions that live in the front matter of those skills, because that's going to be the teaser that the model gets to determine whether or not it should invoke a particular skill. So we get to go from a short little snippet describing what capabilities are available to the detailed instructions the model should follow.

MITCH: Yeah, we actually have a Codex sub-agent whose entire job is to spin off versions of the sub-agent that will test for different skills. It'll give examples of different instructions and see if it actually triggered the skill, if the sub-agent grabbed the skill or not — as a way to pseudo-test whether the front matter descriptions work well.

[00:57:30] CHRISTINE: And then Ryan, what about specific skills in our library?

RYAN: Which library?

CHRISTINE: Uh, this was a follow-up question for the app store.

RYAN: Oh. I really like using the Figma skill. It's super super neat to close the loop from work that other members of my team are doing, to pull that context into Codex. In the same way we're doing all these tricks with Slack to bring context into the codebase as well.

[00:58:01] CHRISTINE: Nice. Okay, I'm curious if any work was put into creating a bootstrap for harness engineering on a brownfield application — for example, documentation management, generic rules and conventions — and if not, what sort of specific implementation details could you advise on?

RYAN: Yeah. We are still actively figuring out what it means to deploy these techniques into a brownfield codebase, and this is something we're super happy to collaborate with the community on to figure out what works. In general, the techniques we've been doing are to carve apart parts of the repository into isolated business logic domains, add interfaces, add high-quality local documentation on the best practices that every member of the team who owns this code is looking for. So we've been having individual doc subtrees that are close to the code that's being modified, using that same sort of structure that we lay out.

And yes, turn on all the lints you can.

[00:59:04] CHRISTINE: Okay. Do you have any resources or examples for these markdown prompt files to help guide Codex with long-running tasks?

CHARLIE: I mean, I'll let Ryan answer, but I think all the skills we've had, the metrics that we've shown, and the code for the sample app — we're going to have that in the Build Hours GitHub repository. So you can take a look at how we're asking the model to grade these markdown prompt files.

RYAN: Yeah. And I'll drop those links after this session in a follow-up email. Mitch, there were some questions for you too — people were really interested in your slide deck as well as Paper.

RYAN: One thing I'll say is: to see these files — what reliability looks like for your codebase, what security looks like, what front-end component architecture looks like — just sit down as a team and rapid-fire throw some bullets on a whiteboard around what you think good looks like. And these can be pretty high level, right? Like something like "secure code has secure interfaces that are impossible to misuse" is just something you should write down. And just getting a couple of files in the codebase that have the seeds of this makes it really, really easy to incrementally add to them. So take the time as a team to figure out what good looks like for you.

CHARLIE: Cool. Yeah, like I said, it'll be in GitHub.

[01:00:21] CHRISTINE: Awesome. And with that, we will wrap up. Here are some additional resources, but again, I will send them out post-session. And then just a quick plug on upcoming Build Hours: we have two coming up — one on agent capabilities happening March 24th, and then GPT Realtime 1.5 on April 15th. Follow the link below — that's our homepage where you can find past recorded sessions as well as sign up for everything that's coming up. And with that, we will wrap up. Thank you so much for attending, and thanks Mitch for joining us. Have a good one.

MITCH: Thanks, fam. Happy building.
