# -*- coding: utf-8 -*-
# (c) YashDK [yash-dk@github]
# (c) modified by AmirulAndalib [amirulandalib@github]
import logging
from ...functions.Human_Format import human_readable_bytes, human_readable_timedelta
from ..getVars import get_val
from telethon.errors.rpcerrorlist import MessageNotModifiedError, FloodWaitError
from telethon.tl.types import KeyboardButtonCallback
from datetime import datetime

torlog = logging.getLogger(__name__)

class Status():
    # Shared List
    Tasks = []
    
    def __init__(self):
        self._task_id = len(self.Tasks) + 1

    def refresh_info(self):
        raise NotImplementedError

    def update_message(self):
        raise NotImplementedError

    def is_active(self):
        raise NotImplementedError

    def set_inactive(self):
        raise NotImplementedError

# qBittorrent Task Class
class QBTask(Status):
    
    def __init__(self, torrent, message, client):
        super().__init__()
        self.Tasks.append(self)
        self.hash = torrent.hash
        self._torrent = torrent
        self._message = message
        self._client = client
        self._active = True
        self._path = torrent.save_path
        self._error = ""
        self._done = False
        self.cancel = False
        self._omess = None
        self._prevmsg = ""
    
    async def set_original_mess(self, omess):
        self._omess = omess
    
    async def get_original_message(self):
        return self._omess

    async def refresh_info(self, torrent = None):
        if torrent is None:
            self._torrent = self._client.torrents_info(torrent_hashes=self._torrent.hash)
        else:
            self._torrent = torrent

    async def get_sender_id(self):
        return self._omess.sender_id

    async def create_message(self):
        msg = "\n<b> ╭─────「 ⏬ 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 ⏬ 」</b>\n<b>│</b>\n<b>├</b> <code>{}</code>".format(
            self._torrent.name
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Down:</b> {} <b>Up:</b> {}".format(
            human_readable_bytes(self._torrent.dlspeed,postfix="/s"),
            human_readable_bytes(self._torrent.upspeed,postfix="/s")
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Progress:</b> {} - {}%".format(
            self.progress_bar(self._torrent.progress),
            round(self._torrent.progress*100,2)
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Downloaded:</b> {} of {}".format(
            human_readable_bytes(self._torrent.downloaded),
            human_readable_bytes(self._torrent.total_size)
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>ETA:</b> <b>{}</b>".format(
            human_readable_timedelta(self._torrent.eta)
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>S:</b>{} <b>L:</b>{}".format(
            self._torrent.num_seeds,self._torrent.num_leechs
            )
        msg += "\n<b>│</b>\n<b>╰────「</b> <b>Using engine:</b> <code>qBittorrent</code> <b>」</b>"

        return msg

    async def get_state(self):
        #stalled
        if self._torrent.state == "stalledDL":
            return"🚦𝗧𝗼𝗿𝗿𝗲𝗻𝘁 <code>{}</code> 𝗶𝘀 𝘀𝘁𝗮𝗹𝗹𝗲𝗱(𝘄𝗮𝗶𝘁𝗶𝗻𝗴 𝗳𝗼𝗿 𝗰𝗼𝗻𝗻𝗲𝗰𝘁𝗶𝗼𝗻)𝘁𝗲𝗺𝗽𝗼𝗿𝗮𝗿𝗶𝗹𝘆.".format(self._torrent.name)
        #meta stage
        elif self._torrent.state == "metaDL":
            return  "🧲𝗚𝗲𝘁𝘁𝗶𝗻𝗴 𝗺𝗲𝘁𝗮𝗱𝗮𝘁𝗮 𝗳𝗼𝗿 {} - {}".format(self._torrent.name,datetime.now().strftime("%H:%M:%S"))
        elif self._torrent.state == "downloading" or self._torrent.state.lower().endswith("dl"):
            # kept for past ref
            return None

    async def central_message(self):
        cstate = await self.get_state()
        if cstate is not None:
            return cstate
        else:
            return await self.create_message()

    async def update_message(self):
        msg = await self.create_message()
        if self._prevmsg == msg:
            return

        self._prevmsg = msg
        
        try:
        
            cstate = await self.get_state()
            
            msg = cstate if cstate is not None else msg
            
            await self._message.edit(msg,parse_mode="html",buttons=self._message.reply_markup) 

        except MessageNotModifiedError as e:
            torlog.debug("{}".format(e))
        except FloodWaitError as e:
            torlog.error("{}".format(e))
        except Exception as e:
            torlog.info("Not expected {}".format(e))


    async def set_done(self):
        self._done = True
        await self.set_inactive()

    def is_done(self):
        return self._done

    async def set_path(self, path):
        self._path = path

    async def get_path(self):
        return self._path

    async def set_inactive(self, error=None):
        self._active = False
        if error is not None:
            self._error = error

    async def is_active(self):
        return self._active

    def progress_bar(self, percentage):
        """Returns a progress bar for download
        """
        #percentage is on the scale of 0-1
        comp = get_val("COMPLETED_STR")
        ncomp = get_val("REMAINING_STR")
        pr = ""

        for i in range(1,11):
            if i <= int(percentage*10):
                pr += comp
            else:
                pr += ncomp
        return pr


class ARTask(Status):
    
    def __init__(self, gid, message, aria2, dl_file):
        super().__init__()
        self.Tasks.append(self)
        self._gid = gid
        self._dl_file = dl_file 
        self._message = message
        self._aria2 = aria2
        self._active = True
        self._error = ""
        self._done = False
        self.cancel = False
        self._omess = None
        self._path =None 
        self._prevmsg = ""
    # Setters

    async def set_original_mess(self, omess=None):
        if omess is None:
            omess = await self._message.get_reply_message()

        self._omess = omess

    async def get_original_message(self):
        return self._omess

    async def get_gid(self):
        return self._gid

    async def set_gid(self, gid):
        self._gid = gid
    
    async def get_sender_id(self):
        return self._omess.sender_id

    async def refresh_info(self, dl_file = None):
        if dl_file is None:
            try:
                self._dl_file = self._aria2.get_download(self._gid)
            except:
                torlog.exception("Errored in fetching the direct DL.")
        else:
            self._dl_file = dl_file

    async def create_message(self):
        # Getting the vars pre handed
        downloading_dir_name = "N/A"
        try:
            downloading_dir_name = str(self._dl_file.name)
        except:
            pass

        msg = "\n<b> ╭─────「 ⏬ 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 ⏬ 」</b>\n<b>│</b>\n<b>├</b> <code>{}</code>".format(
            downloading_dir_name
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Down:</b> {} <b>Up:</b> {}".format(
            self._dl_file.download_speed_string(),
            self._dl_file.upload_speed_string()
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Progress:</b> {} - {}%".format(
            self.progress_bar(self._dl_file.progress/100),
            round(self._dl_file.progress,2)
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Downloaded:</b> {} of {}".format(
            human_readable_bytes(self._dl_file.completed_length),
            human_readable_bytes(self._dl_file.total_length)
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>ETA:</b> <b>{}</b>\n".format(
            self._dl_file.eta_string()
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Conns:</b>{} <b>".format(
            self._dl_file.connections
            )
        msg += "\n<b>│</b>\n<b>╰────「</b> <b>Using engine:</b> <code>Aria2 For DirectLinks</code> <b>」</b>"

        return msg

    async def get_state(self):
        # No states for aria2
        pass

    async def central_message(self):
        return await self.create_message()

    async def update_message(self):
        msg = await self.create_message()
        if self._prevmsg == msg:
            return
        
        self._prevmsg = msg
        
        try:
            data = "torcancel aria2 {} {}".format(
                self._gid,
                self._omess.sender_id
            )
            await self._message.edit(msg,parse_mode="html",buttons=[KeyboardButtonCallback("Cancel Direct Leech",data=data.encode("UTF-8"))]) 

        except MessageNotModifiedError as e:
            torlog.debug("{}".format(e))
        except FloodWaitError as e:
            torlog.error("{}".format(e))
        except Exception as e:
            torlog.info("Not expected {}".format(e))

    async def set_done(self):
        self._done = True
        await self.set_inactive()

    def is_done(self):
        return self._done

    async def set_inactive(self, error=None):
        self._active = False
        if error is not None:
            self._error = error

    async def is_active(self):
        return self._active

    async def get_error(self):
        return self._error

    async def set_path(self, path):
        self._path = path

    async def get_path(self):
        return self._path

    def progress_bar(self, percentage):
        """Returns a progress bar for download
        """
        #percentage is on the scale of 0-1
        comp = get_val("COMPLETED_STR")
        ncomp = get_val("REMAINING_STR")
        pr = ""

        for i in range(1,11):
            if i <= int(percentage*10):
                pr += comp
            else:
                pr += ncomp
        return pr

class MegaDl(Status):
    
    def __init__(self, add_info, dl_info, message, mega_client):
        super().__init__()
        self.Tasks.append(self)
        self._gid = add_info["gid"]
        self._dl_info = dl_info
        self._message = message
        self._mega_client = mega_client
        self._active = True
        self._error = ""
        self._done = False
        self.cancel = False
        self._omess = None
        self._path = add_info["dir"] 
        self._prevmsg = ""
    # Setters

    async def set_original_mess(self, omess=None):
        if omess is None:
            omess = await self._message.get_reply_message()

        self._omess = omess

    async def get_original_message(self):
        return self._omess

    async def get_gid(self):
        return self._gid

    async def set_gid(self, gid):
        self._gid = gid
    
    async def get_sender_id(self):
        return self._omess.sender_id

    async def refresh_info(self, dl_info = None):
        if dl_info is None:
            try:
                self._dl_info = self._aria2.get_download(self._gid)
            except:
                torlog.exception("Errored in fetching the direct DL.")
        else:
            self._dl_info = dl_info

    async def create_message(self):
        # Getting the vars pre handed
        

        msg = "\n<b>╭─────「 ⏬ 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 ⏬ 」</b>\n<b>│</b>\n<b>├</b> <code>{}</code>".format(
            self._dl_info["name"]
            )
        msg += "\n<b>│</b>\n<b>├</b>  <b>Speed:</b> {}".format(
            human_readable_bytes(self._dl_info["speed"])
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Progress:</b> {} - {}%".format(
            self.progress_bar((self._dl_info["completed_length"]/self._dl_info["total_length"])),
            round((self._dl_info["completed_length"]/self._dl_info["total_length"])*100, 2)
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>Downloaded:</b> {} of {}".format(
            human_readable_bytes(self._dl_info["completed_length"]),
            human_readable_bytes(self._dl_info["total_length"])
            )
        msg += "\n<b>│</b>\n<b>├</b> <b>ETA:</b> <b>N/A</b> <b>│</b>"
        
        msg += "\n<b>╰────「</b> <b>Using engine:</b> <code>Mega DL</code> <b>」</b>"

        return msg

    async def get_state(self):
        # No states for aria2
        pass

    async def central_message(self):
        return await self.create_message()

    async def update_message(self):
        msg = await self.create_message()
        if self._prevmsg == msg:
            return
        
        self._prevmsg = msg
        
        try:
            data = "torcancel megadl {} {}".format(
                self._gid,
                self._omess.sender_id
            )
            await self._message.edit(msg,parse_mode="html",buttons=[KeyboardButtonCallback("Cancel Mega DL",data=data.encode("UTF-8"))]) 

        except MessageNotModifiedError as e:
            torlog.debug("{}".format(e))
        except FloodWaitError as e:
            torlog.error("{}".format(e))
        except Exception as e:
            torlog.info("Not expected {}".format(e))

    async def set_done(self):
        self._done = True
        await self.set_inactive()

    def is_done(self):
        return self._done

    async def set_inactive(self, error=None):
        self._active = False
        if error is not None:
            self._error = error

    async def is_active(self):
        return self._active

    async def get_error(self):
        return self._error

    async def set_path(self, path):
        self._path = path

    async def get_path(self):
        return self._path

    def progress_bar(self, percentage):
        """Returns a progress bar for download
        """
        #percentage is on the scale of 0-1
        comp = get_val("COMPLETED_STR")
        ncomp = get_val("REMAINING_STR")
        pr = ""

        for i in range(1,11):
            if i <= int(percentage*10):
                pr += comp
            else:
                pr += ncomp
        return pr
