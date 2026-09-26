export default function TopNavigation() {
	return (
		<header className='top-navigation'>
			<a className='brand' href='#/' aria-label='GlobalStat home'>
				<span className='brand-mark' aria-hidden='true' />
				<span>GlobalStat</span>
			</a>

			<nav className='navigation-links' aria-label='Main navigation'>
				<a className='navigation-link' href='#/' aria-current='page'>
					Explore
				</a>

				<button className='navigation-link' type='button' disabled title='Coming soon'>
					Compare
				</button>

				<button className='navigation-link' type='button' disabled title='Coming soon'>
					Insights
				</button>
			</nav>
		</header>
	);
}
