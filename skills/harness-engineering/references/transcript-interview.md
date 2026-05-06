OpenAI's Michael Bolin on Codex, Harness Engineering, and the Real Future of Coding Agents
Turing Post | ~22 min

Speakers:
- Host: Turing Post interviewer
- Michael Bolin: Lead of open-source Codex at OpenAI

---

[00:00:19]

Host: Hello everyone. I'm happy to have Michael Bolin today for the interview. He is the lead for open-source Codex. Michael, thank you for joining me.

Michael: Thank you. It's great to be here. So currently people often think the story of AI coding is just "the model writes code," but a lot of teams building agents say that the real shift is to designing the environment around the models. What side are you on?

[00:00:43]

Host: What side are you on?

Michael: Certainly the model is going to dominate the experience. There's still a lot of room for innovation in the harness — it's not a pure research problem. I would say, in particular for our team, it's been that relationship between the engineering side and the research side and co-developing the agent. Making sure that anyone can have ideas about how the agent should work, making sure that the harness lets the agent shine and do the best things that it can do, giving the right tooling to the agent, and making sure that it gets used in training so that things are in distribution when we ship it as a product to the world.

[00:01:35]

Host: Let's maybe define "harness" and why it becomes so important.

Michael: Sure. The harness — we also call it the agent loop — is the bit that calls out to the model, samples what the model says, and gives it the context of: here's what I'm trying to do, here are the tools available to me, tell me what to do next. Then it gets a response from the model. Often that's a tool call that says: here's the tool I want you to call with these arguments, let me know what came back. Sometimes these tools are pretty straightforward — run this executable, tell me what standard out was, what was the exit code, and that's it. We've done a lot more experiments with more sophisticated tools for controlling the machine, controlling the user's laptop — a more interactive terminal session, not just simple shelling out of commands. Or it could be something like: do this web search. A lot of what we do on Codex in particular — because it is primarily a coding agent and we care tremendously about security and sandboxing — is that the harness takes these shell commands or computer use commands from the model and ensures they run in a sandbox, or under whatever policy the user decided to give the agent. There turns out to be a lot of complexity in that area. It's critical that we not only expose all the intelligence of the model but do it safely on the user's machine.

[00:02:48]

Host: How do you do it when you're open-sourcing Codex?

Michael: The safety side of it, you mean?

Host: Yeah.

Michael: The nice thing is you can actually see all of this because it's in our repo. We do different things for each operating system. On macOS there's a technology called Seatbelt. On Linux we use a collection of libraries — something called Bubblewrap, and seccomp, and Landlock. On Windows we've actually built our own sandbox. Some of these things, like Seatbelt, are part of macOS, so that's not in the open-source repo — just how we call it. But other things, like our Windows sandbox, the code for that is in the open-source repo. We orchestrate all these calls that go through the sandbox in the appropriate way for the different tool calls.

[00:03:33]

Host: So when people fork Codex, it's all baked in — all the safety rules?

Michael: Right. Yes. I should clarify a detail there: there's "safety" and "security" and people use these terms interchangeably in AI a lot, but they are subtly different. The piece I'm talking about is more strictly on the security side — where you're saying: yes, you can run this tool, but you can only read these folders or write these folders, and that sort of thing. I think most people in the industry would clarify that safety is actually happening more on the back end, making sure that the tool calls the model suggests in the first place are safe to run. From the harness's perspective, it's following orders in a certain sense — it's faithfully executing the tool calls — but those decisions about what tool calls are safe or appropriate to run are made by the model. So yes, if you forked Codex and you're still talking to our models and relying on the safety of our models, then yes, you get that. If you ran someone else's model, then it's a little more up in the air.

[00:04:35]

Host: Since you launched Codex, how does it perform? What do you see? It's a little complicated — there's the CLI, there's the app, there's this, there's that. But in general, how has the audience liked it?

Michael: We've had a very positive response. I think it's something like 5x in usage since the start of the year. Going back, we launched in April of last year, but it was really in August when GPT-5 came out. We did a refresh of the CLI — that's when it really started moving. We had growth before, but it really started jumping up. Then we did the VS Code extension later that summer or fall, and people really gravitated toward that. I believe VS Code overtook CLI usage. Then we launched the app at the start of this year and that has really taken off. I think it's really the first of its kind in a lot of ways, and it's resonating with people.

[00:05:27]

Host: What's so new about it?

Michael: Developers had spent so much time in their IDE historically, and it makes sense to meet users where they are. Some users are in the terminal, so that's why we have the CLI. A lot of users are in an IDE, so that's why we're in VS Code — and now also integrated into JetBrains and Xcode. Those are obvious, natural places to meet developers. With the Codex app, we've actually established a new surface. I like to think of it as a mission control type of interface where I'm now managing many conversations in parallel. But it has some key pieces of what you normally expect in a traditional IDE. So you can browse the diff the agent has made. You can pop open a terminal with Command+J, so you don't have to switch to a different window if you want to do something ad hoc. It's really breaking the expectation that "oh, I don't actually have to have all my code visible." I mean, it's nice when you do, but you can actually get a lot done, and there's more value for a lot of people in being able to organize and work across multiple agents. That's actually the thing that's the top priority and what we really bring front and center.

[00:06:39]

Host: Let's talk a little bit about how coding agents and systems like Codex change the way developers work. When coding agents enter the workflow, what changes first in the daily work of engineers like you?

Michael: One of the biggest things is throughput. People realize that if you really put attention on it, you can actually get a lot of work done in parallel. That incurs some amount of context switching that not everyone loves, but if you can master that, you can really push a lot of things forward. Personally, I have five clones of the Codex repo that I can hop between. Sometimes it's a small thing I just spotted while doing something else — I'd just really like to get that fixed. Other times there's a full-day conversation where I'm doing a very large change and working with Codex throughout the course of the day, or between meetings. A lot of people with five minutes between meetings might want to send another message just to push it in another direction so it keeps moving forward on whatever task they're doing.

So: working across multiple work streams at the same time. I think another thing that a lot of people are spending more time on is figuring out how to optimize this workflow. This is all very new to everybody, relatively speaking. Should I turn this thing I keep doing into a skill? Should I share this skill with my teammates because we should all be doing this? Good developers are always trying to find good tools and optimize their inner loop, but this is a new inner loop that we're all figuring out how to optimize.

And then the other one I think is very natural: how much time we all spend on code review, and the volume of code review. That gets a lot of attention right now. Codex is also doing a lot of the code review, which is great — it saves us a lot of time. Figuring out how to make the most of that too always feels like a bit of a moving target right now.

[00:08:44]

Host: When you were working on Codex initially, were there any interesting stories or unexpected things you encountered?

Michael: So much has changed. Codex is still not even quite a year old, which is pretty remarkable given the amount of change in that time period.

Host: Mind-blowing, yeah.

Michael: Yeah. Trying to think back — the models are a very big part of the acceleration we've had. When we launched in April of 2025, that was part of the o3 and o4 mini launch. We were using reasoning models. The tool calling and instruction following weren't quite where we wanted them to be, and seeing that change over time has been a big one. But you asked specifically about early on — a lot of those things... I think getting Codex to write more of Codex was just such an exciting thing to see, that bootstrapping happen. Things like AGENTS.md becoming more standard — getting that scaffolding in place so that you're building the tool that's optimizing your own workflow — that gives you kind of that exponential liftoff. And it was exciting to see colleagues really starting to get it and shift more of their work to Codex.

[00:10:04]

Host: How does a repository and all its documents need to look when an agent is navigating it instead of a human developer? You mentioned AGENTS.md — what's the biggest difference?

Michael: It's funny. I think an interesting thing about this whole agentic coding journey is that there are a number of practices that have been considered best practice in software for a long time, and we just didn't do them. Documentation is one. Test-driven development is another. People did do these things, but there was always "is the trade-off worth it?" And now, in an agent-first world, these things are clearly worth it. People are almost rediscovering things we've known about for a long time, but really caring about them now.

When you think about AGENTS.md — all the stuff that's in there, at least what we write in ours — I would say it's suitable for a human joining the team. It's all these best practices, things they need to know. It's actually kind of freeing to make sure we actually write these things down — for the agent and for our teammates. On Codex, you can actually see ours right in the repo. Our AGENTS.md file is pretty modest. We consider ourselves "AGI-pilled," meaning the agent should really be deciding what to do rather than us feeding it more instruction than it needs. So rather than writing a document that's in parallel to the source code — which is potentially duplicative and also potentially incorrect — the agent most of the time is spending a lot of time ripgrepping through code, forming its own opinion. We try to put things in AGENTS.md that it maybe wouldn't have gotten very obviously or very quickly from the code — like "this is the way you should run the tests" or "these tests are more important than those tests." But we actually try not to overdo it. Let the agent decide the best way forward.

[00:11:55]

Host: So you think in the near future AGENTS.md files will be written by an agent?

Michael: I mean, a lot of people's are right now. I know a lot of folks who — we don't happen to do it on our team as a general practice, but look through the commit history and double-check me on that. Many people I know anecdotally have their personal instructions say something like: "when you're done, please update anything of interest to the AGENTS.md file that wasn't obvious." I see different papers coming out on people experimenting with how much to tell the agent, and I'm sure it depends on the agent as well. Like I said, we take a modest approach — it's not tens of pages of instructions. I think it's more like a handful, off the top of my head.

[00:12:44]

Host: What about context engineering being an important part of this process? Is there such a thing as too much context for an agent?

Michael: I'm not a researcher, so I'd give you a more empirical answer. A lot of times when I'm prompting Codex for a more meaty task, I probably write about a paragraph, and I ask it to go familiarize itself with that part of the code. Maybe I give it explicit pointers to files if I think that'll help, but a lot of times I don't — it does a good job searching the codebase. I think subtly making sure files and folders are well named and things like that — that's just good practice anyway, but it's probably even more important than we realize when the agent is searching the code.

Most of the context is going to be AGENTS.md, the thing I prompted, and maybe some file references I gave it. I also give it access to reading GitHub, so I can say things like: "a similar thing happened in this pull request" or "I think this was discussed in this pull request," and it can see not just the code but the conversation that happened on that pull request. Again, it's more about letting Codex know it has these options — here are the tools in your toolbox — without being prescriptive about the best way for it to solve a problem. Trying to let it do its job. It's a good model, so it does a good job there.

Host: It sounds like that almost pushes you toward stricter architecture.

[00:14:18]

Michael: Certainly. Codex is going to follow patterns that it sees in the codebase. So if you have a good architecture in the first place, it's going to follow it, maintain it, and enforce the invariants you set up — you're going to be in a good position over time. But again, that's also true of human developers. It's just that the rate of change is now so much higher, so if you do have these standards, you're going to get the benefits of them.

[00:14:44]

Host: Do you still see a lot of slop coming out from the model, from coding agents, and how do you fight it?

Michael: With Codex, nothing comes to mind that I would call slop. Sometimes all these models just like to write code, so sometimes the answer is deleting code, and you need to be a little more prescriptive in that way. But that's not exactly slop. Or maybe it's: "you added 500 lines to this file, maybe you should have made a new file" — those are easier fixes. In many cases, what's far more common is that it knows an idiom or a language feature that I just happen to not have encountered yet, and it adds it and I learn something new. That is more often the way I'm surprised by Codex, rather than the other way.

[00:15:30]

Host: What you're describing is that since Codex was started, the model wasn't there yet. Now it's a much stronger model, and now it's the application itself that's bringing more audience. I'm trying to understand this — big model or big harness, what is more important? And is there a point where the harness stops being a wrapper and starts becoming an environment that matters more, or does the model still rule it all?

Michael: It's possible. In a lot of ways we try to make the harness as small and as tight as possible. One thing you see in Codex compared to some others is that we try to give it very few tools. For example, Codex doesn't have an explicit tool for reading files. Instead, we give it control of a computer terminal, and if it uses cat or sed or whatever command-line tool is present on the system to read a file, we encourage it to do that. I made a comment earlier about being "AGI-pilled," meaning we give it a large space to play in and it should find the best point in that space to move forward. In a certain sense the harness gets smaller — we try to keep it small and just give it a handful of very powerful tools.

The only place we perhaps compromise on that is the security aspect. The sandboxing — specifically how we approach it — is a very important backstop to just letting Codex run wild. Sometimes people try tricks with special tools to manage the context window better. As the harness author you might feel like: "I know better than Codex, I'm going to try to bias it to do certain things, like manage the context window better." But we try to shy away from that. If it's going to run a tool that spits out a gigabyte of data, we don't want to put that gigabyte into the context window because it's probably not relevant. Our view would be: let's bias Codex so that it writes that to a file and then maybe it greps the file or does something else — but again it's free to choose its own way to solve that problem.

[00:17:39]

Host: Do you think it's possible to encode all these rules in safety and build it into sandboxing, or should there always be a human in the loop for human judgment?

Michael: For coding at least, for the tasks I focus on, sandboxing is really the main thing — it's the replacement for human in the loop for a lot of this stuff. You have a problem, a coding problem that you give to Codex. You have this environment that it can operate in, constrained in certain ways by a sandbox. Letting it explore that space is going to get you the best solution. Certainly at scale — I mentioned I have five clones of Codex going — if I were having to interject every few minutes on all five of those, that really fundamentally limits the throughput you can get out of them. In training the model, as opposed to having a human in the loop, we want the models to get smarter and to do those types of corrections at training time, and then have that play out at inference time.

[00:18:45]

Host: So it will be more in the model, not in the harness.

Michael: Yes. There are other parts that are important too, right? Things like the reliability of the harness is a pretty big one. If the harness falls over, then your session's over, and what can the model do? So performance and reliability are very important principles when implementing the harness. For example, if you're running a farm of Raspberry Pis where each one's running the agent loop, you want to be judicious with resources on the machine so that most of the energy is spent on what the model needs to do, and the harness is ideally doing the bare minimum there.

I think we'll inevitably move toward multi-agent and sub-agent architectures — more agents talking across machines and things like that. Having the harness span not just a single machine process but a whole network of agents — I expect there'll be interesting work to do there still. I won't be out of a job quite yet. That will change. I've personally spent most of my career writing tools for developers, and now I'm probably writing more tools for agents. The agent can obviously write its own tools as well, but we'd rather have a small number of very powerful tools that it can use to explore the space. We'll also continue experimenting with what that right set of primitives should be.

[00:20:16]

Host: Do you know what that set is already? Have you thought about it?

Michael: I think we see a lot of the pieces right now. I mentioned a "shell tool" earlier — I use "terminal tool" more generally. The model interfaces with a computer terminal more like a human would, not just by executing individual commands straight up. So dealing with things like streaming output and using that efficiently.

The use of memory is another big area with a lot of interesting work happening. Historically, every time you start a conversation it's kind of from nothing — that's why you have AGENTS.md and some of this context stuffing, to get information into the model quickly. If you look in the repo, you can see there are a lot of experiments around memory. There's a lot going on with different types of context connectors. Originally it was kind of focused on computer tasks on your machine, but now it's also about getting work done in the broader sense — sending email on your behalf, creating documents, taking action in a web browser. There's a lot there as well.

And then things like standard LLM stuff — generally speaking, more context window is good. How we compact that when you hit the limits of the context window — all that is still being actively pursued and contributes to the overall agent experience.
