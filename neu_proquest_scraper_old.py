import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

pageNum = 2
hasNextPage = True

# setup variables
TARGET_YEAR_FROM = 2019
TARGET_YEAR_TO = 2019
SEARCH_KEYWORDS = ["certiorari", "plaintiff", "appeals court", "state supreme court"]
FILENAME = "proquest_articles"

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
    getArticles()
    
    # TODO: if hits the last page, stop

    goToPageGroup = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "jumptoPage")))
    print(goToPageGroup.text)
    pageIndexInput = goToPageGroup.find_element(By.CLASS_NAME, "pageIndex")
    print(pageIndexInput.text)
    pageIndexInput.clear()
    pageIndexInput.send_keys(pageNum)
    pageButton = goToPageGroup.find_element(By.ID, "submit_5")
    print(pageButton.text)
    pageButton.click()

# function to get each of the articles once search is complete
def getArticles():
    WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "resultItems")))
    ul_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "resultItems"))
    )
    li_elements = ul_element.find_elements(By.CLASS_NAME, "resultItem")
    
    try: 
        for li in li_elements:
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
            print(f"Year {year_from} to {year_to} Filter applied.")
            break
        except Exception as e:
            print("Filter cannot be applied, tring once more.")
            attempts += 1
            time.sleep(3)
    if attempts == max_attempts:
        print("Filter cannot be applied, exiting selenium")
        driver.quit()
    print("--")
    
# after clicking on the article, get the content of the article
def getArticleContent(href):
    try:
        full_text = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "fullTextZone"))
        )
        text = full_text.text
    except:
        text = None
        
    # clicking on the details button
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
            print(f"Error: neither citaion nor abstract exist")
            try:
                assignmentAndSaveArticles(text, href)
            except Exception as e:
                print(f"No article details at all.")
    
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
        saveArticles(newspaper, location, date, title, text, author, url=href)
    except Exception as e:
        print(f"Error: {e}")
    
# get other article details
def getArticleDetails():
    newspaper, location, date, title, author = None, None, None, None, None
    parent_divs = WebDriverWait(driver, 2).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'display_record_indexing_row'))
    )
        
    for div in parent_divs:
        field_name = div.find_element(By.CLASS_NAME, 'display_record_indexing_fieldname').text
        
        if field_name.strip() == 'Publisher':
            newspaper = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
            # print(f"newspaper: {newspaper}")
        
        if field_name.strip() == 'Country of publication':
            location = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
            # print(f"location: {location}")
            
        if field_name.strip() == 'Publication date':
            date = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
            # print(f"date: {date}")
        
        if field_name.strip() == 'Title':
            title = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
            # print(f"Title: {title}")
            
        if field_name.strip() == 'Author':
            author = div.find_element(By.CLASS_NAME, 'display_record_indexing_data').text
            # print(f"Author: {author}")
            
    return newspaper, location, date, title, author

# Closing any banners
def closeBanner():
    try:
        consent_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))
        )
        consent_button.click()
    except Exception as e:
        print(f"Consent banner not found or already closed: {e}")
        
    try:
        WebDriverWait(driver, 3).until(
            EC.invisibility_of_element((By.CLASS_NAME, 'onetrust-pc-dark-filter'))
        )
    except Exception as e:
        print(f"Overlay did not disappear: {e}")
        
# function to save to csv
def saveArticles(newspaper, location, date, title, text, author, url):
    if not os.path.isfile(f'{FILENAME}.csv'):
        df = pd.DataFrame(columns=["Newspaper", "Location", "Date", "Title", "Text", "Author", "URL"])
        df.to_csv(f'{FILENAME}.csv', index=False)
    
    df = pd.read_csv(f'{FILENAME}.csv')
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
    
    df.to_csv(f'{FILENAME}.csv', index=False)

# TODO: clean text content, symbols, etc.

if __name__ == "__main__":
    search_term = " OR ".join(SEARCH_KEYWORDS)
    print(f"Search term: {search_term}")
    
    options = webdriver.ChromeOptions()

    driver = webdriver.Chrome(options=options)

    driver.get("https://www.proquest.com/usnews/news/fromDatabasesLayer?accountid=12826")
    time.sleep(20)

    search_by_title(driver, search_term)
    filterByYear(TARGET_YEAR_FROM, TARGET_YEAR_TO)
    
    while hasNextPage:
        nextPage()
        print(f"hasNextPage {hasNextPage}")
        pageNum += 1

    driver.quit()
