import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

pageNum = 2
hasNextPage = True
ARTICLE_COUNT = 0
MAX_ARTICLES = 100
MIN_KEYWORDS = 4

# set up variables
DEFAULT_YEAR_FROM = 2017
DEFAULT_YEAR_TO = 2020
DEFAULT_KEYWORDS = ["certiorari", "appeal", "court", "jurisdiction", 
                    "litigation", "lawsuit", "plaintiff", "disposition", 
                    "legality", "constitution", "constitutionality", "unconstitutional",
                    "rulings", "upheld", "bill of rights", "amendment",
                    "overturn", "overturn", "affirmed", "reversed"]

EXCLUDED_KEYWORDS = []
FILENAME = "proquest_articles"

# create the folder if it doesn't exist
DATA_FOLDER = "proquest_scraper_data"
os.makedirs(DATA_FOLDER, exist_ok=True)

#formats new filename
def get_next_filename():
    base_filename = FILENAME
    counter = 1
    while os.path.isfile(os.path.join(DATA_FOLDER, f'{base_filename}_{counter}.csv')):
        counter += 1
    return os.path.join(DATA_FOLDER, f'{base_filename}_{counter}.csv')

current_filename = get_next_filename()
excluded_filename = current_filename.replace(".csv", "_excluded.csv")

df = pd.DataFrame(columns=["Newspaper", "Location", "Date", "Title", "Text", "Author", "URL"])
df_excluded = pd.DataFrame(columns=["Newspaper", "Location", "Date", "Title", "Text", "Author", "URL"])
df.to_csv(current_filename, index=False)
df_excluded.to_csv(excluded_filename, index=False)

# function used to search by the title once logged in
def search_by_title(driver, docket_title):
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "searchTerm")))
    text_box = driver.find_element(by=By.ID, value="searchTerm")
    submit_button = driver.find_element(by=By.ID, value="expandedSearch")
    closeBanner()
    text_box.send_keys(docket_title)
    submit_button.click()

# goes to the next page until message spotted on page
def nextPage():
    global hasNextPage
    global pageNum
    global ARTICLE_COUNT

    # check if the maximum number of articles has been reached
    if ARTICLE_COUNT >= MAX_ARTICLES:
        hasNextPage = False
        print("Maximum number of articles reached. Stopping the scraper.")
        return

    getArticles()

    # if hits the last page, stop
    try:
        goToPageGroup = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "jumptoPage")))
        pageIndexInput = goToPageGroup.find_element(By.CLASS_NAME, "pageIndex")
        pageIndexInput.clear()
        pageIndexInput.send_keys(pageNum)
        pageButton = goToPageGroup.find_element(By.ID, "submit_5")
        pageButton.click()
        pageNum += 1

    except:
        hasNextPage = False
        print("Reached the last page. Stopping the scraper.")
        return

# function to get each of the articles once search is complete
def getArticles():
    print(f"getting articles for page {pageNum - 1}")
    global ARTICLE_COUNT
    global hasNextPage

    WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "resultItems")))
    ul_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "resultItems"))
    )
    li_elements = ul_element.find_elements(By.CLASS_NAME, "resultItem")

    try:
        for li in li_elements:
            if ARTICLE_COUNT >= MAX_ARTICLES:
                hasNextPage = False
                print("Maximum number of articles reached. Stopping the scraper.")
                return
            
            time.sleep(3)
            a_element = li.find_element(By.CLASS_NAME, 'previewTitle')
            href = a_element.get_attribute('href')
            
            if href and href != 'javascript:void(0)':
                print("---")
                print(f"Navigating to: {href}")
                driver.execute_script(f"window.open('{href}', '_blank');")
                driver.switch_to.window(driver.window_handles[-1])

                getArticleContent(href)
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'resultItems'))
                )
                
                time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
     
# function to filter by year
def filterByYear(year_from, year_to):
    print("--")
    print("Applying year filter: ")
    startDate = str(year_from) + "-01-01"
    endDate = str(year_to) + "-12-31"
    enterField = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "upDateDateRangeLink"))
    )

    enterField.click()

    startDateField = driver.find_element(by=By.ID, value="startingDate")
    startDateField.clear()
    startDateField.send_keys(startDate)

    endingDateField = driver.find_element(by=By.ID, value="endingDate")
    endingDateField.clear()
    endingDateField.send_keys(endDate)
    endingDateField.send_keys(Keys.RETURN)
    area = driver.find_element(By.ID, value="dateFilter-div")
    submitButton = area.find_element(By.CSS_SELECTOR, "a#dateRangeSubmit.btn.btn-default")
    max_attempts = 5
    attempts = 0

    while attempts < max_attempts:
        try:
            submitButton.click()
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'applied-filters'))
            )
            print(f"Year {year_from} to {year_to} filter applied.")
            break
        except Exception as e:
            print("Filter cannot be applied, trying once more.")
            attempts += 1
            time.sleep(1)
    if attempts == max_attempts:
        print("Filter cannot be applied, exiting selenium")
        driver.quit()
    print("--")

#cuts off the text displayed if character count of article exceeds cell character limit
def text_cutoff(text, limit):
    if len(text) > limit:
        print(f"Text length ({len(text)}) exceeds {limit} characters limit; truncating.")
        return text[:limit]
    return text


# after clicking on the article, get the content of the article
def getArticleContent(href):
    try:
        full_text = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "fullTextZone"))
        )
        text = full_text.text
    except:
        text = None
        
    contentsButton = None
    try:
        contentsButton = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "addFlashPageParameterformat_citation"))
        )
    except:
        try:
            contentsButton = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "addFlashPageParameterformat_abstract"))
            )
        except Exception as e:
            print("Error: neither citation nor abstract exist")
            try:
                assignmentAndSaveArticles(text, href)
            except Exception as e:
                print("No article details at all.")

    if contentsButton:  
        href = contentsButton.get_attribute('href')
        if href and href != 'javascript:void(0)':
            driver.get(href)
            assignmentAndSaveArticles(text, href)
            time.sleep(1)
            driver.back()

# function to assign and save articles
def assignmentAndSaveArticles(text, href):
    try:
        newspaper, location, date, title, author = getArticleDetails()
        print(newspaper, location, date, title, author)
        is_valid = isValidArticle(text)
        saveArticles(newspaper, location, date, title, text, author, url=href, is_valid=is_valid)
    except Exception as e:
        print(f"Error: {e}")

# get other article details
def getArticleDetails():
    newspaper, location, date, title, author = None, None, None, None, None
    parent_divs = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'display_record_indexing_row'))
    )
    # for i, div in enumerate(parent_divs):
    #     print(f"--- Div {i+1} ---")
    #     print(div.get_attribute('outerHTML'))
    #     print(f"--- End of Div {i+1} ---")
    for div in parent_divs:
        try:
            field_name = div.find_element(By.CLASS_NAME, 'display_record_indexing_fieldname').text
        except:
            continue
        
        if field_name.strip() == 'Publisher':
            newspaper = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
        
        if field_name.strip() == 'Country of publication':
            location = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
            
        if field_name.strip() == 'Publication date':
            date = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
        
        if field_name.strip() == 'Title':
            title = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
            
        if field_name.strip() == 'Author':
            author = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
            
    return newspaper, location, date, title, author

# closing any banners (mainly cookie banner)
def closeBanner(max_attempts=3):
    for attempt in range(max_attempts):
        try:
            consent_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))
            )
            consent_button.click()
            
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, 'onetrust-pc-dark-filter'))
            )
            print("Consent banner closed successfully.")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
    
    print("Failed to close consent banner after multiple attempts.") 
    return False

# function to save to csv
def saveArticles(newspaper, location, date, title, text, author, url, is_valid):
    global ARTICLE_COUNT, current_filename, excluded_filename

    excel_char_count = 32767

    if text:
        text = text_cutoff(text, excel_char_count)

    if is_valid:
        df = pd.read_csv(current_filename)
        new_row = pd.DataFrame([{
            "Newspaper": newspaper,
            "Location": location,
            "Date": date,
            "Title": title,
            "Text": text,
            "Author": author,
            "URL": url
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(current_filename, index=False)
        ARTICLE_COUNT += 1
    else:
        df_excluded = pd.read_csv(excluded_filename)
        new_row_excluded = pd.DataFrame([{
            "Newspaper": newspaper,
            "Location": location,
            "Date": date,
            "Title": title,
            "Text": text,
            "Author": author,
            "URL": url
        }])
        df_excluded = pd.concat([df_excluded, new_row_excluded], ignore_index=True)
        df_excluded.to_csv(excluded_filename, index=False)

def isValidArticle(text):
    total_keywords = 0
    for word in DEFAULT_KEYWORDS:
        if(word in text):
            total_keywords += 1
        print (total_keywords)
        if(total_keywords >= MIN_KEYWORDS):
            return True
    print("Not enough keywords in article; not added to CSV.")
    return False


# formats proquest search given keywords.
def create_proquest_search_string():
    search_string = f'({" OR ".join(f"\"{keyword}\"" for keyword in DEFAULT_KEYWORDS)})'

    if SEARCH_KEYWORDS:
        search_string += f' AND ({" AND ".join(f"\"{keyword}\"" for keyword in SEARCH_KEYWORDS)})'
    if EXCLUDED_KEYWORDS != []:
        search_string += f' NOT ({" AND ".join(f"\"{keyword}\"" for keyword in EXCLUDED_KEYWORDS)})'

    return search_string

# run the script
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ProQuest Article Scraper")
    parser.add_argument("--max_articles", type=int, default=100, help="Maximum number of articles to scrape")
    parser.add_argument("--year_from", type=int, default=DEFAULT_YEAR_FROM, help="Starting year for filtering")
    parser.add_argument("--year_to", type=int, default=DEFAULT_YEAR_TO, help="Ending year for filtering")
    parser.add_argument("--keywords", type=str, default="", help="Comma-separated keywords for search")

    args = parser.parse_args()

    MAX_ARTICLES = args.max_articles
    TARGET_YEAR_FROM = args.year_from
    TARGET_YEAR_TO = args.year_to
    SEARCH_KEYWORDS = [keyword.strip() for keyword in args.keywords.split(",") if keyword.strip()]

    search_term = create_proquest_search_string()

    options = webdriver.ChromeOptions()
    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://www.proquest.com/usnews/news/fromDatabasesLayer?accountid=12826")
    wait = WebDriverWait(driver, 300)
    login_success_element = wait.until(EC.presence_of_element_located((By.ID, "searchTerm")))

    search_by_title(driver, search_term)
    filterByYear(TARGET_YEAR_FROM, TARGET_YEAR_TO)

    while hasNextPage:
        nextPage()

    driver.quit()
