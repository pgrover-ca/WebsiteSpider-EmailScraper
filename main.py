import re
import asyncio
import aiohttp
from email_validator import validate_email, EmailNotValidError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import ssl
import certifi


# Get all the links from the user-defined URL.


async def get_user_input():
    while True:
        user_url = input("Enter the URL of the webpage to spider links from: ")
        if await is_valid_url(user_url):
            return user_url
        print("Invalid URL. Please enter a valid URL.")


async def is_valid_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, ssl=ssl.create_default_context(cafile=certifi.where())) as response:
                return response.status == 200
    except aiohttp.ClientError:
        return False


async def fetch(url, ssl_context):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        # print(f"Searching {url} ...")
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, ssl=ssl_context) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(
                        f"Failed to fetch the webpage. Status code: {response.status}")
                    return None
    except aiohttp.ClientError as e:
        print(f"Error occurred while fetching URL: {e}")
        return None


async def get_links_with_full_url(url, ssl_context):
    page_content = await fetch(url, ssl_context)
    if page_content:
        soup = BeautifulSoup(page_content, "html.parser")
        base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
        links = [urljoin(base_url, link.get("href"))
                 for link in soup.find_all("a", href=True) if not link.get("href").startswith("mailto:")]
        return links
    else:
        return []


async def scrape_emails(url, ssl_context):
    page_content = await fetch(url, ssl_context)
    if page_content:
        # Regular Expression to match email addresses
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(email_pattern, page_content)

        # Perform email validation asynchronously
        valid_emails = await validate_emails(emails)

        return valid_emails
    else:
        return []


async def validate_emails(emails):
    valid_emails = []
    for email in emails:
        try:
            valid_email = validate_email(email)
            valid_emails.append(valid_email.email)
        except EmailNotValidError:
            pass  # Ignore invalid emails silently
    return valid_emails


async def main():
    user_url = await get_user_input()
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    try:
        async with aiohttp.ClientSession() as session:
            crawled_link_list = set(await get_links_with_full_url(user_url, ssl_context))

            all_emails = []  # Create an empty list to store all the emails from all URLs
            processed_urls = []  # Create an empty list to store the processed URLs

            tasks = [scrape_emails(url, ssl_context)
                     for url in crawled_link_list]
            for url, task in zip(crawled_link_list, asyncio.as_completed(tasks)):
                emails_from_url = await task
                all_emails.extend(emails_from_url)
                processed_urls.append(url)

            # Perform email validation asynchronously
            valid_emails = await validate_emails(all_emails)

            # Remove duplicates from valid_emails list
            valid_emails = list(set(valid_emails))

            if valid_emails:
                print("\nValid emails: \n")
                for email in valid_emails:
                    print(email)
            else:
                print("No valid emails found in the list.")

            if processed_urls:
                print("\nProcessed URLs: \n")
                for url in processed_urls:
                    print(url)

    except aiohttp.ClientError as e:
        print(f"Error occurred while fetching URL: {e}")

if __name__ == "__main__":
    asyncio.run(main())
