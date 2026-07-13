# Janet | 👩🏽‍🏫 (not a girl)
Janet (not a [girl](https://www.youtube.com/watch?v=HicS3qBJ0y4)) is a collection of common faculty administrative functions in one easy to use docker container and Gradio app!

I vibecoded Janet from Google and Brave's free AI modes, I'm sorry.

# 👩🏽‍🏫 Janet can:

<details>
<summary><b>📅 Generate a syllabus calendar with repeating assignments</b></summary>

- It can overlay an ICS calendar file from upload or a weblink.
- This means your institutional calendar can be overlayed on top of your syllabus.
- You can edit and download your completed course calendar, or cut/paste directly into an LMS (Canvas)

</details>

<details>
<summary><b>📊 Convert class point values to a GPA decimal and/or alphanumeric grade</b></summary>

- This is useful for submitting final grade rosters
- You can customize your own/institutional grade matrix

</details>

<details>
<summary><b>📝 Generate assignment feedback from templates</b></summary>

- You can make unlimited custom assignment rubrics/outputs
- You can batch grade a class and save the batch as a CSV/excel file
- You can cut/paste directly into an LMS

</details>

<details>
<summary><b>📣 Generate LMS announcements that give students a weekly agenda</b></summary>

- Never screw up what day a Friday/Monday is!
- Make your announcements consistently clear!

</details>

<details>
<summary><b>🛡️ Generate canned/semi-canned emails to students</b></summary>

- Remind a student they missed a deadline
- Warn a student about behavior or grades
- Tell a student on waitlist you aren't allowing overloads!
- "Can it, [Janet!"](https://www.youtube.com/watch?v=t4WP3bODmfo)

</details>


# 👩🏽‍🏫 Janet IS:

<details>
<summary><b>👩🏾‍⚖️ FERPA friendly</b></summary>

- No student record/data is saved on the server.
- ALL work is held only in the browser session. Close the tab and poof, it's gone.
- All CSVs are 'deliberative' or 'process' documents, so they shouldn't need record retention.
- Be extra compliant by not using last names or avoiding names all together.

</details>

<details>
<summary><b>⚙️ Adaptable</b></summary>

- Most sections allow you to template custom responses.
- You can edit/download/upload new templates as you wish.

</details>

<details>
<summary><b>🔒 Secure</b></summary>

- The application is built on Gradio, so you get all the API and security options.
- Runs in docker, so you control this.

</details>

# 🚀 Deployment Guides


<details>
<summary><b>🐳 Deploy via Docker CLI</b></summary>

### Quick Setup

1. **Clone the official source repository:**
   ```bash
   git clone https://github.com/wryandginger/janet
   cd janet
   ```

2. **Build the container image layer:**
   ```bash
   docker build -t janetapp .
   ```

3. **Create your local persistent data folders:**
   ```bash
   mkdir -p ./janet_data/templates
   touch ./janet_data/grade_scale.txt
   ```

4. **Launch the application container:**
   Fire up the instance on port `7435` with persistent volume mappings:
   ```bash
   docker run -d \
     -p 7435:7435 \
     -e GRADIO_AUTH_USER=professor \
     -e GRADIO_AUTH_PASSWORD=SetYourSecurePasswordHere123! \
     -v ./janet_data/grade_scale.txt:/app/grade_scale.txt \
     -v ./janet_data/templates:/app/templates_dir \
     --name janet_app \
     --restart unless-stopped \
     janetapp
   ```

</details>

<details>
<summary><b>🚢 Deploy via Portainer Web UI Stack Repository</b></summary>

### Web Dashboard Configuration Step-by-Step

1. **Create a New Web Stack via Git Repository:**
   - Navigate to your Portainer web portal dashboard.
   - Click on **Stacks** in the left sidebar menu, and press the **Add stack** button.
   - Under **Build method**, select **Repository**.

2. **Configure Git Repository Settings:**
   - **Repository URL**: Paste the official repository path: `https://github.com/wryandginger/janet/`
   - Leave the rest as default in this top section.

3. **🚨 CRITICAL: Adjust Environment Variables inside Portainer:**
   Scroll down to the **Environment variables** configuration section on the page. Click **Add environment variable** to override your app's default login security values:
   - Set `GRADIO_AUTH_USER` to your preferred username (e.g., `professor`).
   - Set `GRADIO_AUTH_PASSWORD` to a strong unique credential password.

4. **🚨 CRITICAL: Verify/Change Your Host Local Volume Mount Points:**
   Portainer deploys stack folders out of a default directory. To change where your text templates and grade rules are permanently saved on your server's host file system, deploy the default project from github. Then detach the stack from github. You should then be able to change the `docker-compose.yml` properties or add host volume path adjustments:
   - By default, the repository's compose setup maps local data to relative paths `./janet_data/...` relative to where Portainer pulls the repository branch files.
   - To force files to save to an absolute directory layout path on your server's machine instead, use an absolute path syntax layout map like:
     ```text
     /home/your_user/janet_data/grade_scale.txt:/app/grade_scale.txt
     /home/your_user/janet_data/templates:/app/templates_dir
     ```

5. **Deploy the Stack:**
   Scroll to the bottom of the Portainer interface screen and click **Deploy the stack**. By default, Janet will run at the host IP:7435

</details>


