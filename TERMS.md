# TERMS AND RESPONSIBLE USE POLICY

## ⚠️ Responsible Use & Authentication Policy

JobFunnel provides scraping and browser-automation capabilities using
Playwright. Use of JobFunnel is entirely optional, and you are solely
responsible for how you access third-party websites through this tool.

This section explains how JobFunnel handles authentication, how you must use it,
and what JobFunnel does not do.

## 🔐 Authentication & Login-Required Sites

Some job boards (e.g., LinkedIn, Glassdoor) require a user login before viewing
listings. JobFunnel supports this only through a user-initiated Playwright login
flow: 1. JobFunnel opens a real Playwright browser window. 2. You manually log
in to the site using the browser. 3. Playwright saves an encrypted storageState
file on your local machine. 4. JobFunnel reuses that local session to load pages
while scraping.

✔️ What JobFunnel does do • Allows you to authenticate using your own browser
session • Saves Playwright storage state only on your machine • Uses that
session to load pages inside a controlled Playwright browser • Keeps everything
local and private

✖️ What JobFunnel does NOT do • Does not ever see, store, transmit, or log your
username or password • Does not collect, upload, or analyze cookies or session
data • Does not bypass CAPTCHAs, 2FA, or security features • Does not circumvent
paywalls, access controls, or protections • Does not guarantee compliance with
any website’s Terms of Service

You remain fully in control of your credentials and session data at all times.

## 📌 Your Responsibilities

By using JobFunnel, you agree that: • You are responsible for complying with the
Terms of Service of any website you access. • You understand that scraping some
websites may be restricted or disallowed. • You will use your own account and
will not automate access to accounts you do not own. • You control and manage
your own authentication files (\*.auth.json, storageState.json). • You will not
share, upload, or commit authentication files or cookies.

JobFunnel is a browser automation tool, not a service provider. You assume all
responsibility for how you use it.

## 🔒 Security Recommendations

To protect yourself: • Keep your \*.auth.json files private and local • Add them
to .gitignore (JobFunnel does this by default) • Regenerate your session
periodically • Do not distribute or publish any authentication data • Use a
dedicated “scraping” account if possible

JobFunnel operates entirely on your local machine and does not transmit or store
any private credentials.

## 📄 Disclaimer

JobFunnel is provided as a general-purpose browser automation and data
collection tool. It does not provide legal advice, guarantee compliance with
third-party Terms of Service, or make any representations about the legality of
scraping any particular website. Use of JobFunnel is entirely at your own risk.

By using JobFunnel, you agree to the following:

1. You assume full responsibility for how you access and interact with
   third-party websites. This includes compliance with all applicable laws,
   regulations, and Terms of Service.

2. The maintainers, contributors, and authors of JobFunnel are not liable for
   any actions you take while using this software, including (but not limited
   to) account restrictions, IP blocks, data loss, legal claims, or violation of
   third-party Terms.

3. JobFunnel does not encourage, facilitate, or enable bypassing security,
   access controls, CAPTCHAs, paywalls, authentication requirements, or rate
   limits imposed by websites.

4. JobFunnel does not collect, transmit, store, or access your credentials,
   cookies, or browsing data. All authentication files and sessions remain
   entirely under your control.

5. JobFunnel is provided “as-is” with no warranty of any kind, express or
   implied. The maintainers make no guarantees regarding availability,
   correctness, reliability, or fitness for any particular purpose.

6. You agree to indemnify and hold harmless the authors and contributors of
   JobFunnel from any claims, damages, or liabilities arising from your use or
   misuse of the software.

By installing, using, or running JobFunnel, you acknowledge and accept these
terms.
