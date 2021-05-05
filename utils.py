def get_btn_text_from_cb_data(message: dict, callback_data: str) -> str:
	"""Retrieves button text from callback data (update.callback_query.data) using update.callback_query.message"""
	for lst in message['reply_markup']['inline_keyboard']:
		btn = lst[0]
		if btn['callback_data'] == callback_data:
			return btn['text']


def re_one_from_menu(menu_keyboard: list[list]) -> str:
	"""Generates regex based on existing menu keyboard that matches exactly one element"""
	re_str = '^('
	for idx_l, lst in enumerate(menu_keyboard):
		for idx_str, str_ in enumerate(lst):
			re_str += str_
			if (idx_l + 1 != len(menu_keyboard)) and (idx_str + 1 != len(lst)):
				re_str += '|'
	re_str += ')$'
	return re_str
