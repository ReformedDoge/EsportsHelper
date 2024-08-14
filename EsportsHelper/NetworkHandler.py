import json

from selenium.common import WebDriverException

from EsportsHelper.Config import config
from EsportsHelper.Logger import log
from EsportsHelper.I18n import i18n
from EsportsHelper.Stats import stats
from time import sleep

_ = i18n.getText
_log = i18n.getLog


class NetworkHandler:
    def __init__(self, driver):
        self.driver = driver
        pass


def getRewardByLog(driver, isInit=False):
    """
    Extract reward and watch hour data from browser performance logs.

    This function retrieves reward and watch hour data from the browser's performance logs. It parses the logs and extracts
    the relevant information, updating the appropriate statistics variables accordingly.

    Parameters:
    driver: WebDriver instance representing the browser.
    isInit (bool): Flag indicating whether the data is for initialization or not. Defaults to False.
    """
    max_retries = 6
    retry_delay = 6  # seconds
    retry_count = 0

    while retry_count < max_retries:
        try:
            performanceLog = driver.get_log('performance')
            if not performanceLog:
                log.warning("Performance log is empty.")
                retry_count += 1
                sleep(retry_delay)
                continue

            sleep(5)  # Allow some time for logs to accumulate
            log.info(f"Performance log length: {len(performanceLog)}")
            found_earned_drops = False

            for packet in performanceLog:
                try:
                    message = json.loads(packet.get('message')).get('message')
                    if message.get('method') != 'Network.responseReceived':
                        continue
                    
                    url = message.get('params').get('response').get('url')
                    requestId = message.get('params').get('requestId')
                    
                    if "earnedDrops" in url:
                        found_earned_drops = True
                        log.info(f"earnedDrops URL found: {url}")
                        resp = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': requestId})
                        dropList = json.loads(resp["body"])
                        log.info(f"dropList length: {len(dropList)}")
                        
                        if isInit:
                            stats.initDropsList = dropList
                        else:
                            stats.currentDropsList = dropList
                        
                        log.info(f"Stats updated - isInit: {isInit}, initDropsList length: {len(stats.initDropsList)}")
                        log.info(f"Stats updated - isInit: {isInit}, currentDropsList length: {len(stats.currentDropsList)}")
                    
                    elif "stats?sport=lol" in url:
                        resp = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': requestId})
                        watchHour = json.loads(resp["body"])[0]["statValue"]
                        if isInit:
                            stats.initWatchHour = watchHour
                        else:
                            stats.currentWatchHour = watchHour
                        log.info(f"Stats updated - isInit: {isInit}, WatchHour: {watchHour}")
                
                except json.JSONDecodeError as json_error:
                    log.error(f"Failed to decode JSON from log packet: {json_error}")
                except KeyError as key_error:
                    log.error(f"Missing key in log packet: {key_error}")
                except Exception as e:
                    # detached too quickly while a request was being handled
                    continue
            
            if not found_earned_drops:
                log.error("earnedDrops not found in the performance log. Refreshing the driver...")
                driver.refresh()
                retry_count += 1
                sleep(retry_delay)
            else:
                break
        
        except WebDriverException as e:
            log.error(f"WebDriverException occurred while getting log data")
            retry_count += 1
            sleep(retry_delay)
        except Exception as e:
            log.error(f"Exception occurred while getting log data")
            retry_count += 1
            sleep(retry_delay)
    
    if retry_count >= max_retries:
        log.error("Max retries reached. Unable to retrieve reward data.")
    else:
        log.info("Log data retrieval successful.")
