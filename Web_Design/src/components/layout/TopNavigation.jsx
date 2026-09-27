export default function TopNavigation() {
	return (
		<header className='top-navigation'>
			<a className='brand' href='#/' aria-label='HerTime home'>
				<svg className='brand-mark' viewBox='160 180 404 400' aria-hidden='true' focusable='false'>
					<image href={`${import.meta.env.BASE_URL}brand/globalstat-logo-dark.png`} width='1944' height='809' />
				</svg>
				<span>HerTime</span>
			</a>

			<nav className='navigation-links' aria-label='Main navigation'>
				<a className='navigation-link' href='#/explore'>Explore ↗</a>
			</nav>
		</header>
	);
}
